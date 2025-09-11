"""
Setup Flow Middleware - Manages user onboarding and setup completion
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from company.models import UserCompanyAccess
from setup.models import CompanySetupStatus


class SetupFlowMiddleware(MiddlewareMixin):
    """
    Middleware to handle automatic setup flow redirection
    """
    
    # URLs that don't require setup completion
    EXEMPT_URLS = [
        # Authentication
        '/users/login/',
        '/users/logout/',
        '/users/register/',
        '/accounts/login/',
        
        # Setup flow URLs (allow access during setup)
        '/setup/',
        '/company/create/',
        '/company/switch/',
        
        # Static/media files
        '/static/',
        '/media/',
        
        # Admin
        '/admin/',
        
        # API endpoints
        '/api/',
    ]
    
    # URLs patterns that should be exempt (using startswith)
    EXEMPT_PATTERNS = [
        '/setup/',
        '/company/create',
        '/company/switch',
        '/users/',
        '/admin/',
        '/api/',
        '/static/',
        '/media/',
    ]

    def process_request(self, request):
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
            
        # Skip for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
            
        # Skip if URL is in exempt list
        current_path = request.path
        if self.is_exempt_url(current_path):
            return None
            
        # Check user's company setup status
        redirect_url = self.check_setup_requirements(request)
        if redirect_url:
            return redirect(redirect_url)
            
        return None
    
    def is_exempt_url(self, path):
        """Check if the URL should be exempt from setup checks"""
        # Exact matches
        if path in self.EXEMPT_URLS:
            return True
            
        # Pattern matches
        for pattern in self.EXEMPT_PATTERNS:
            if path.startswith(pattern):
                return True
                
        return False
    
    def check_setup_requirements(self, request):
        """
        Check if user needs to be redirected for setup
        Returns redirect URL or None
        """
        user = request.user
        
        # Step 1: Check if user has any companies
        user_companies = UserCompanyAccess.objects.filter(user=user).select_related('company')
        
        if not user_companies.exists():
            # New user - needs to create first company
            messages.warning(
                request, 
                "🏢 Welcome! Let's start by creating your first company."
            )
            return reverse('company:company_create')
        
        # Step 2: Check if user has an active company
        active_company = self.get_active_company(request)
        if not active_company:
            # User has companies but none selected - redirect to company selection
            messages.info(
                request,
                "📋 Please select a company to continue."
            )
            return reverse('company:company_list')
        
        # Step 3: Check setup completion for active company
        try:
            setup_status = CompanySetupStatus.objects.get(company=active_company)
            completion_percentage = setup_status.completion_percentage
            
            if completion_percentage < 50:  # Minimum threshold for basic usage
                # Critical setup steps missing
                messages.warning(
                    request,
                    f"⚙️ Please complete the setup for {active_company.name}. "
                    f"({completion_percentage:.0f}% complete)"
                )
                return reverse('setup:dashboard')
                
        except CompanySetupStatus.DoesNotExist:
            # No setup status record - needs setup
            CompanySetupStatus.objects.create(company=active_company)
            messages.warning(
                request,
                f"🚀 Let's set up {active_company.name} to get started!"
            )
            return reverse('setup:dashboard')
        
        # All checks passed - no redirect needed
        return None
    
    def get_active_company(self, request):
        """Get the user's currently active company"""
        from company.views import get_active_company
        return get_active_company(request)


class SetupCompletionMiddleware(MiddlewareMixin):
    """
    Middleware to add setup completion status to all requests
    """
    
    def process_request(self, request):
        # Add setup status to request for templates
        if request.user.is_authenticated:
            request.setup_status = self.get_setup_status(request)
        return None
    
    def get_setup_status(self, request):
        """Get comprehensive setup status for current user/company"""
        from company.views import get_active_company
        
        active_company = get_active_company(request)
        
        if not active_company:
            return {
                'has_company': False,
                'needs_setup': True,
                'completion_percentage': 0,
                'next_step': 'create_company',
                'setup_url': reverse('company:company_create')
            }
        
        try:
            setup_status = CompanySetupStatus.objects.get(company=active_company)
            completion_percentage = setup_status.completion_percentage
            
            return {
                'has_company': True,
                'needs_setup': completion_percentage < 100,
                'completion_percentage': completion_percentage,
                'next_step': setup_status.next_step,
                'setup_url': reverse('setup:dashboard'),
                'company': active_company
            }
            
        except CompanySetupStatus.DoesNotExist:
            return {
                'has_company': True,
                'needs_setup': True,
                'completion_percentage': 0,
                'next_step': 'company_info',
                'setup_url': reverse('setup:dashboard'),
                'company': active_company
            }
