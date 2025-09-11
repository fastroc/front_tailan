"""
Context processors for global template variables
"""
from company.models import Company
from company.views import get_active_company


def company_context(request):
    """
    Add company-related context variables to all templates
    """
    context = {
        'active_company': None,
        'user_companies': [],
        'setup_status': None,
    }
    
    if request.user.is_authenticated:
        # Get user's companies
        user_companies = Company.objects.filter(
            user_access__user=request.user,
            is_active=True
        ).distinct().order_by('name')
        
        context['user_companies'] = user_companies
        
        # Get active company using the utility function
        active_company = get_active_company(request)
        context['active_company'] = active_company
        
        # Get setup status for sidebar
        if active_company:
            try:
                from setup.models import CompanySetupStatus
                setup_status = CompanySetupStatus.objects.get(company=active_company)
                context['setup_status'] = {
                    'has_company': True,
                    'needs_setup': setup_status.completion_percentage < 100,
                    'completion_percentage': setup_status.completion_percentage,
                    'next_step': setup_status.next_step,
                    'setup_url': '/setup/',
                    'company': active_company
                }
            except Exception:
                # CompanySetupStatus doesn't exist yet or other error
                context['setup_status'] = {
                    'has_company': True,
                    'needs_setup': True,
                    'completion_percentage': 0,
                    'next_step': 'company_info',
                    'setup_url': '/setup/',
                    'company': active_company
                }
        else:
            # No active company
            context['setup_status'] = {
                'has_company': False,
                'needs_setup': True,
                'completion_percentage': 0,
                'next_step': 'create_company',
                'setup_url': '/company/create/',
                'company': None
            }
    
    return context
