"""
View mixins for multi-company support.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from company.models import Company, UserCompanyAccess, UserCompanyPreference


class CompanyContextMixin:
    """Add company context to views and ensure user has access."""
    
    def get_active_company(self, user=None):
        """Get user's active company."""
        if not user:
            user = getattr(self.request, 'user', None)
            
        if not user or not user.is_authenticated:
            return None
        
        # Try session first for immediate updates
        company_id = self.request.session.get('active_company_id')
        if company_id:
            try:
                company = Company.objects.get(
                    id=company_id,
                    user_access__user=user,
                    is_active=True
                )
                return company
            except Company.DoesNotExist:
                # Clear invalid session data
                if 'active_company_id' in self.request.session:
                    del self.request.session['active_company_id']
        
        # Fall back to user preferences
        try:
            preferences = user.company_preference
            if preferences.active_company and preferences.active_company.is_active:
                # Verify user still has access
                if UserCompanyAccess.objects.filter(
                    user=user,
                    company=preferences.active_company
                ).exists():
                    # Update session for next time
                    self.request.session['active_company_id'] = preferences.active_company.id
                    return preferences.active_company
        except UserCompanyPreference.DoesNotExist:
            pass
        
        # If no active company set, return the first available company
        first_company = Company.objects.filter(
            user_access__user=user,
            is_active=True
        ).first()
        
        if first_company:
            # Set as active company for future requests
            try:
                preferences = user.company_preference
                preferences.active_company = first_company
                preferences.save()
            except UserCompanyPreference.DoesNotExist:
                UserCompanyPreference.objects.create(
                    user=user,
                    active_company=first_company
                )
            
            self.request.session['active_company_id'] = first_company.id
            
        return first_company
    
    def dispatch(self, request, *args, **kwargs):
        """Add company context to request."""
        if request.user.is_authenticated:
            self.active_company = self.get_active_company(request.user)
            # Add to request for easy template access
            request.active_company = self.active_company
        else:
            self.active_company = None
            request.active_company = None
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add company context to template."""
        context = super().get_context_data(**kwargs)
        context['active_company'] = self.active_company
        return context


class CompanyRequiredMixin(CompanyContextMixin):
    """Require user to have an active company to access view."""
    
    company_required_message = "Please select a company to continue."
    company_required_redirect = "company:company_list"
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if request.user.is_authenticated and not self.active_company:
            messages.warning(request, self.company_required_message)
            return redirect(self.company_required_redirect)
            
        return response


class CompanyAccessMixin(CompanyRequiredMixin):
    """Ensure user has specific access level to the company."""
    
    required_role = None  # 'owner', 'admin', 'user'
    access_denied_message = "You do not have permission to access this resource."
    
    def get_user_company_access(self, user=None, company=None):
        """Get user's access level for the company."""
        if not user:
            user = self.request.user
        if not company:
            company = self.active_company
            
        if not user or not company:
            return None
            
        try:
            return UserCompanyAccess.objects.get(
                user=user,
                company=company
            )
        except UserCompanyAccess.DoesNotExist:
            return None
    
    def check_company_permission(self, user_access):
        """Check if user has required permission level."""
        if not user_access:
            return False
            
        if not self.required_role:
            return True  # No specific role required
            
        # Define role hierarchy
        role_hierarchy = {
            'owner': 3,
            'admin': 2,
            'user': 1
        }
        
        required_level = role_hierarchy.get(self.required_role, 0)
        user_level = role_hierarchy.get(user_access.role, 0)
        
        return user_level >= required_level
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if isinstance(response, redirect().__class__):
            return response  # Already redirecting
            
        if request.user.is_authenticated and self.active_company:
            user_access = self.get_user_company_access()
            
            if not self.check_company_permission(user_access):
                messages.error(request, self.access_denied_message)
                raise PermissionDenied(self.access_denied_message)
                
        return response
    
    def get_context_data(self, **kwargs):
        """Add user access info to context."""
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated and self.active_company:
            context['user_company_access'] = self.get_user_company_access()
        return context
