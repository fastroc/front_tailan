from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from company.models import Company
from .models import CompanySetupStatus
from .setup_steps.company_info import CompanyInfoSetupStep
from .setup_steps.tax_setup import TaxSetupStep


# Define available setup steps
SETUP_STEPS = {
    'company_info': CompanyInfoSetupStep,
    'tax_setup': TaxSetupStep,
}


def get_active_company(request):
    """Get the active company for the user"""
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            return Company.objects.get(
                id=company_id,
                user_access__user=request.user
            )
        except Company.DoesNotExist:
            pass
    
    # If no active company, try to get the first one
    user_companies = Company.objects.filter(
        user_access__user=request.user
    ).first()
    
    if user_companies:
        request.session['active_company_id'] = user_companies.id
        return user_companies
    
    return None


@login_required
def setup_dashboard(request):
    """Main setup dashboard showing all setup steps"""
    active_company = get_active_company(request)
    
    if not active_company:
        messages.warning(request, 'Please create or select a company first.')
        return redirect('company:company_list')
    
    # Get or create setup status
    setup_status, created = CompanySetupStatus.objects.get_or_create(
        company=active_company
    )
    
    # Build setup steps data
    setup_steps = []
    for step_key, step_class in SETUP_STEPS.items():
        step_instance = step_class(active_company)
        is_complete = step_instance.is_complete(active_company)
        setup_steps.append({
            'key': step_key,
            'name': step_instance.name,
            'description': step_instance.description,
            'required': step_instance.required,
            'complete': is_complete,
            'status_class': step_instance.get_status_class(active_company),
            'status_icon': step_instance.get_status_icon(active_company),
            'url': reverse('setup:step', kwargs={'step_name': step_key}),
            'can_start': step_instance.can_start(active_company)
        })
        
        # Update setup status based on actual step completion
        if step_key == 'company_info' and is_complete and not setup_status.company_info_complete:
            setup_status.company_info_complete = True
        elif step_key == 'tax_setup' and is_complete and not setup_status.tax_complete:
            setup_status.tax_complete = True
    
    # Save any updates to setup status
    setup_status.save()
    
    # Calculate overall progress
    total_steps = len(setup_steps)
    completed_steps = sum(1 for step in setup_steps if step['complete'])
    completion_percentage = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
    
    # Also use the model's completion percentage which uses weights
    model_completion = setup_status.completion_percentage
    
    # Find next step to complete
    next_step = None
    for step in setup_steps:
        if not step['complete'] and step['can_start']:
            next_step = step
            break
    
    context = {
        'active_company': active_company,
        'setup_status': setup_status,
        'setup_steps': setup_steps,
        'completion_percentage': model_completion,  # Use weighted completion from model
        'visual_completion': completion_percentage,  # Simple count for reference
        'next_step': next_step,
        'is_setup_complete': model_completion >= 80,
        'required_complete': setup_status.required_steps_complete
    }
    
    return render(request, 'setup/dashboard.html', context)


@login_required
def setup_step(request, step_name):
    """Handle individual setup step"""
    active_company = get_active_company(request)
    
    if not active_company:
        messages.warning(request, 'Please create or select a company first.')
        return redirect('company:company_list')
    
    if step_name not in SETUP_STEPS:
        messages.error(request, 'Invalid setup step.')
        return redirect('setup:dashboard')
    
    step_class = SETUP_STEPS[step_name]
    step_instance = step_class(active_company)
    
    # Check if step can be started
    if not step_instance.can_start(active_company):
        messages.warning(request, 'Please complete previous setup steps first.')
        return redirect('setup:dashboard')
    
    if request.method == 'POST':
        form_class = step_instance.get_form_class()
        if form_class:
            form = form_class(request.POST, request.FILES)
            if form.is_valid():
                success = step_instance.process_form(form, active_company, request)
                if success:
                    messages.success(request, f'{step_instance.name} completed successfully!')
                    return redirect('setup:dashboard')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            # Handle steps without forms
            messages.error(request, 'This step cannot be processed.')
    
    # Get context for rendering
    context = step_instance.get_context(active_company, request)
    context.update({
        'step_name': step_name,
        'step_instance': step_instance,
        'active_company': active_company
    })
    
    return render(request, step_instance.template_name, context)


@login_required
def skip_step(request, step_name):
    """Skip an optional setup step"""
    active_company = get_active_company(request)
    
    if not active_company:
        return redirect('company:company_list')
    
    if step_name not in SETUP_STEPS:
        messages.error(request, 'Invalid setup step.')
        return redirect('setup:dashboard')
    
    step_class = SETUP_STEPS[step_name]
    step_instance = step_class(active_company)
    
    if step_instance.required:
        messages.warning(request, 'Cannot skip required setup steps.')
        return redirect('setup:dashboard')
    
    messages.info(request, f'{step_instance.name} skipped. You can complete it later.')
    return redirect('setup:dashboard')


@login_required
def complete_setup(request):
    """Mark setup as complete and redirect to main dashboard"""
    active_company = get_active_company(request)
    
    if not active_company:
        messages.warning(request, 'Please create or select a company first.')
        return redirect('company:company_list')
    
    setup_status, created = CompanySetupStatus.objects.get_or_create(
        company=active_company
    )
    
    # Debug: Let's see what the actual completion status is
    completion_percentage = setup_status.completion_percentage
    
    # Additional debug info
    debug_info = {
        'company_info_complete': setup_status.company_info_complete,
        'accounts_complete': setup_status.accounts_complete,
        'tax_complete': setup_status.tax_complete,
        'balance_complete': setup_status.balance_complete,
        'completion_percentage': completion_percentage,
        'required_steps_complete': setup_status.required_steps_complete,
    }
    
    # Add debug message
    messages.info(request, f'Setup Status Debug: {debug_info}')
    
    if completion_percentage >= 50:  # Company info complete (50%)
        # Mark company setup as complete
        active_company.setup_complete = True
        active_company.save(update_fields=['setup_complete'])
        
        # Set completion timestamp if not already set
        if not setup_status.setup_completed_at:
            from django.utils import timezone
            setup_status.setup_completed_at = timezone.now()
            setup_status.save()
        
        messages.success(request, f'Setup completed! Welcome to your accounting system. ({completion_percentage}% complete)')
        return redirect('dashboard')
    else:
        messages.warning(request, f'Please complete more setup steps first. Currently {completion_percentage}% complete. Required steps complete: {setup_status.required_steps_complete}')
        return redirect('setup:dashboard')


@login_required
def debug_setup_status(request):
    """Debug view to check setup status"""
    active_company = get_active_company(request)
    
    if not active_company:
        return redirect('company:company_list')
    
    from django.http import JsonResponse
    from coa.models import Account, TaxRate
    
    setup_status, created = CompanySetupStatus.objects.get_or_create(
        company=active_company
    )
    
    # Check each step manually
    step_checks = {}
    
    # Company info check
    step_checks['company_info'] = {
        'model_complete': setup_status.company_info_complete,
        'actual_complete': bool(active_company.description),
        'description_exists': bool(active_company.description),
        'description_value': active_company.description or 'None'
    }
    
    # Accounts check
    cash_exists = Account.objects.filter(company=active_company, account_type='CURRENT_ASSET').exists()
    income_exists = Account.objects.filter(company=active_company, account_type__in=['REVENUE', 'SALES']).exists()
    expense_exists = Account.objects.filter(company=active_company, account_type='EXPENSE').exists()
    accounts_complete = cash_exists and income_exists and expense_exists
    
    step_checks['accounts'] = {
        'model_complete': setup_status.accounts_complete,
        'actual_complete': accounts_complete,
        'cash_exists': cash_exists,
        'income_exists': income_exists,
        'expense_exists': expense_exists,
        'total_accounts': Account.objects.filter(company=active_company).count()
    }
    
    # Tax check
    tax_exists = TaxRate.objects.filter(company=active_company).exists()
    step_checks['tax'] = {
        'model_complete': setup_status.tax_complete,
        'actual_complete': tax_exists,
        'tax_count': TaxRate.objects.filter(company=active_company).count()
    }
    
    # Balance check
    cash_accounts = Account.objects.filter(company=active_company, account_type='CURRENT_ASSET')
    balance_set = any(account.ytd_balance != 0 for account in cash_accounts)
    step_checks['balance'] = {
        'model_complete': setup_status.balance_complete,
        'actual_complete': balance_set,
        'cash_account_count': cash_accounts.count(),
        'balances': [(acc.code, acc.name, acc.ytd_balance) for acc in cash_accounts]
    }
    
    debug_data = {
        'company_name': active_company.name,
        'setup_status_id': setup_status.id,
        'completion_percentage': setup_status.completion_percentage,
        'required_steps_complete': setup_status.required_steps_complete,
        'all_steps_complete': setup_status.all_steps_complete,
        'step_details': step_checks,
        'raw_model_data': {
            'company_info_complete': setup_status.company_info_complete,
            'accounts_complete': setup_status.accounts_complete,
            'tax_complete': setup_status.tax_complete,
            'balance_complete': setup_status.balance_complete,
        }
    }
    
    return JsonResponse(debug_data, indent=2)
