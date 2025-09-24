"""
Views for loan_reconciliation_bridge app
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import LoanGLConfiguration
from .forms import LoanGLConfigurationForm
from company.views import get_active_company
from coa.models import Account


@login_required
def setup_gl_configuration(request):
    """Setup page for configuring Loan Payments Received account only"""
    
    # Get user's active company
    company = get_active_company(request)
    if not company:
        from company.models import Company
        company = Company.objects.first()
        if not company:
            messages.error(request, 'No companies found. Please create a company first.')
            return redirect('company:company_list')
    
    # Get existing configuration
    config = None
    try:
        config = LoanGLConfiguration.objects.get(company=company)
    except LoanGLConfiguration.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = LoanGLConfigurationForm(request.POST, instance=config, company=company)
        if form.is_valid():
            config = form.save(commit=False)
            config.company = company
            config.save()
            messages.success(request, 'Loan Payments Received account configured successfully!')
            return redirect('loan_reconciliation_bridge:setup_gl_configuration')
    else:
        form = LoanGLConfigurationForm(instance=config, company=company)
    
    # Get available GL accounts for dropdowns - show all company accounts
    accounts = Account.objects.filter(
        company=company
    ).order_by('code')
    
    return render(request, 'loan_reconciliation_bridge/setup.html', {
        'form': form,
        'config': config,
        'accounts': accounts,
        'company': company,
    })
