"""
Context processors for global template variables
"""
from company.models import UserCompanyRole


def company_context(request):
    """
    Add company-related context variables to all templates
    """
    context = {
        'active_company': None,
        'user_companies': [],
    }
    
    if request.user.is_authenticated:
        # Get user's companies
        user_companies = UserCompanyRole.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('company').order_by('company__name')
        
        context['user_companies'] = user_companies
        
        # Get active company from session
        active_company_id = request.session.get('active_company_id')
        if active_company_id:
            try:
                active_company_role = user_companies.get(company_id=active_company_id)
                context['active_company'] = active_company_role.company
            except UserCompanyRole.DoesNotExist:
                pass
        
        # If no active company but user has companies, set the first one as active
        if not context['active_company'] and user_companies.exists():
            first_company = user_companies.first()
            context['active_company'] = first_company.company
            request.session['active_company_id'] = str(first_company.company.id)
    
    return context
