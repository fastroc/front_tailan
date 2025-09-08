from django.urls import path
from django.shortcuts import redirect

app_name = 'setup'

def redirect_to_company_create(request):
    """Redirect old setup URLs to new company creation"""
    return redirect('company:company_create')

def redirect_to_company_list(request):
    """Redirect old setup URLs to company dashboard"""
    return redirect('company:company_list')

urlpatterns = [
    # Redirect old setup wizard to new company system
    path('company/', redirect_to_company_create, name='company_wizard'),
    path('financial-year/', redirect_to_company_create, name='financial_year_wizard'),
    path('opening-balances/', redirect_to_company_list, name='opening_balances_wizard'),
    path('completion/', redirect_to_company_list, name='setup_completion'),
    
    # Legacy API endpoint - return empty response
    path('api/status/', redirect_to_company_list, name='setup_status_api'),
]
