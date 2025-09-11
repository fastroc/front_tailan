"""
Company-aware managers and mixins for multi-tenant architecture.
"""
from django.db import models


class CompanyManager(models.Manager):
    """Manager that provides company-aware filtering."""
    
    def for_company(self, company):
        """Get objects for a specific company."""
        if not company:
            return self.none()
        return self.filter(company=company)
    
    def for_user_company(self, user):
        """Get objects for user's active company."""
        if not user or not user.is_authenticated:
            return self.none()
            
        # Try to get active company from user preferences
        try:
            preferences = user.company_preference
            if preferences.active_company and preferences.active_company.is_active:
                return self.filter(company=preferences.active_company)
        except Exception:
            pass
        
        # Fall back to first company user has access to
        from company.models import Company
        first_company = Company.objects.filter(
            user_access__user=user,
            is_active=True
        ).first()
        
        if first_company:
            return self.filter(company=first_company)
            
        return self.none()
    
    def for_session_company(self, request):
        """Get objects for company stored in session."""
        if not request or not request.user.is_authenticated:
            return self.none()
            
        company_id = request.session.get('active_company_id')
        if company_id:
            from company.models import Company
            try:
                company = Company.objects.get(
                    id=company_id,
                    user_access__user=request.user,
                    is_active=True
                )
                return self.filter(company=company)
            except Company.DoesNotExist:
                pass
                
        # Fall back to user's active company
        return self.for_user_company(request.user)


class CompanyQuerySet(models.QuerySet):
    """QuerySet with company-aware methods."""
    
    def for_company(self, company):
        """Filter by company."""
        if not company:
            return self.none()
        return self.filter(company=company)
    
    def for_user(self, user):
        """Filter by user's accessible companies."""
        if not user or not user.is_authenticated:
            return self.none()
        
        from company.models import Company
        accessible_companies = Company.objects.filter(
            user_access__user=user,
            is_active=True
        )
        
        return self.filter(company__in=accessible_companies)


class CompanyAwareManager(CompanyManager):
    """Combined manager with both Manager and QuerySet methods."""
    
    def get_queryset(self):
        return CompanyQuerySet(self.model, using=self._db)
    
    def for_company(self, company):
        return self.get_queryset().for_company(company)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
