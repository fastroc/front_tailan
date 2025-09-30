"""
Views for loan_reconciliation_bridge app
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal

from .models import LoanGLConfiguration
from .forms import LoanGLConfigurationForm
from company.views import get_active_company
from coa.models import Account


def calculate_payment_allocation(payment, gl_config):
    """
    Calculate payment allocation breakdown for four-tier system.
    
    Args:
        payment: Payment object to allocate
        gl_config: LoanGLConfiguration object
        
    Returns:
        dict: Allocation breakdown with late_fees, interest, principal, and total
    """
    payment_amount = Decimal(str(payment.payment_amount))
    
    # Calculate allocations based on configured percentages
    late_fee_percentage = gl_config.default_late_fee_percentage / Decimal('100')
    interest_percentage = gl_config.default_interest_percentage / Decimal('100')
    
    # Calculate amounts
    late_fees = payment_amount * late_fee_percentage
    interest = payment_amount * interest_percentage  
    principal = payment_amount - late_fees - interest
    
    # Ensure principal is not negative
    if principal < 0:
        # Adjust if percentages exceed 100%
        total_percentage = late_fee_percentage + interest_percentage
        if total_percentage > 1:
            # Scale down proportionally
            scale_factor = Decimal('0.95') / total_percentage  # Leave 5% for principal minimum
            late_fees = payment_amount * late_fee_percentage * scale_factor
            interest = payment_amount * interest_percentage * scale_factor
            principal = payment_amount - late_fees - interest
    
    return {
        'late_fees': late_fees.quantize(Decimal('0.01')),
        'interest': interest.quantize(Decimal('0.01')),
        'principal': principal.quantize(Decimal('0.01')),
        'total': payment_amount,
    }


@login_required
def setup_gl_configuration(request):
    """Setup page for configuring Four-Tier Payment Allocation system"""
    
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
            
            # Mark setup as completed with different levels
            if config.is_five_tier_complete():
                config.setup_completed = True
                messages.success(request, 'Five-tier payment allocation system configured successfully! All accounts including auto-matching are now set up.')
            elif config.is_three_tier_complete():
                config.setup_completed = True  # Core functionality complete
                messages.success(request, 'Four-tier payment allocation system configured successfully! Add General Loan Disbursements for auto-matching.')
            else:
                config.setup_completed = False
                messages.warning(request, 'Configuration saved, but please configure all core accounts for complete setup.')
            
            config.save()
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


# Payment approval views removed - migrated to loan progress engine approach
# Journal creation logic preserved for loan progress engine integration

def create_split_journal_entries(payment, allocation, config, created_by):
    """
    Utility function to create split journal entries for payment allocation
    This will be used by the loan progress engine approval workflow
    """
    from journal.models import Journal, JournalLine
    
    # Create split journal entries
    journal = Journal.objects.create(
        company=payment.loan.company,
        narration=f"Manager Approved Payment Allocation - {payment.payment_id}",
        reference=f"SPLIT-{payment.payment_id}",
        date=payment.payment_date,
        created_by=created_by,
        status='posted'
    )
    
    # DEBIT: General Loans Receivable (Main Engine Account) - this reduces the receivable
    JournalLine.objects.create(
        journal=journal,
        description=f"Payment Allocation Split - {payment.loan.loan_number}",
        account_code=config.general_loans_receivable_account.code,
        company=payment.loan.company,
        debit=payment.payment_amount,
        credit=Decimal('0.00')
    )
    
    # CREDIT: Late Fee Income Account (if any)
    late_fee_amount = allocation.get('late_fees', Decimal('0.00'))
    if late_fee_amount > 0:
        JournalLine.objects.create(
            journal=journal,
            description=f"Late Fee Allocation - {payment.loan.loan_number}",
            account_code=config.late_fee_income_account.code,
            company=payment.loan.company,
            debit=Decimal('0.00'),
            credit=late_fee_amount
        )
    
    # CREDIT: Interest Income Account (if any)
    interest_amount = allocation.get('accrued_interest', Decimal('0.00')) + allocation.get('current_interest', Decimal('0.00'))
    if interest_amount > 0:
        JournalLine.objects.create(
            journal=journal,
            description=f"Interest Allocation - {payment.loan.loan_number}",
            account_code=config.interest_income_account.code,
            company=payment.loan.company,
            debit=Decimal('0.00'),
            credit=interest_amount
        )
    
    # CREDIT: Principal Allocation Account
    principal_amount = allocation.get('principal', Decimal('0.00')) + allocation.get('prepayment', Decimal('0.00'))
    if principal_amount > 0:
        JournalLine.objects.create(
            journal=journal,
            description=f"Principal Allocation - {payment.loan.loan_number}",
            account_code=config.principal_account.code,
            company=payment.loan.company,
            debit=Decimal('0.00'),
            credit=principal_amount
        )
    
    # Update account balances
    config.principal_account.update_balance_from_journals()
    config.interest_income_account.update_balance_from_journals()
    config.late_fee_income_account.update_balance_from_journals()
    
    return journal


@login_required
def reset_split_approvals(request):
    """Reset all split approvals and GL account balances"""
    if request.method != 'POST':
        return redirect('loan_reconciliation_bridge:setup_gl_configuration')
    
    company = get_active_company(request)
    
    try:
        # Get GL configuration
        config = LoanGLConfiguration.objects.get(company=company)
    except LoanGLConfiguration.DoesNotExist:
        messages.error(request, 'Four-tier GL configuration not found. Please configure first.')
        return redirect('loan_reconciliation_bridge:setup_gl_configuration')
    
    try:
        from journal.models import Journal
        
        # Count existing split journals
        split_journals = Journal.objects.filter(
            company=company,
            reference__startswith='SPLIT-PAY'
        )
        journal_count = split_journals.count()
        
        if journal_count == 0:
            messages.info(request, 'No split approvals found to reset.')
            return redirect('loan_reconciliation_bridge:setup_gl_configuration')
        
        # Get the payment IDs from split journals to reset their status
        split_payment_ids = []
        for journal in split_journals:
            # Extract payment ID from reference like "SPLIT-PAY2025155628"
            if journal.reference.startswith('SPLIT-PAY'):
                payment_id = journal.reference.replace('SPLIT-', '')
                split_payment_ids.append(payment_id)
        
        # Delete all split journal entries
        with transaction.atomic():
            split_journals.delete()
            
            # Reset GL account balances for the three accounts (NOT General Loans Receivable)
            # Principal Allocation Account
            config.principal_account.update_balance_from_journals()
            
            # Interest Income Account  
            config.interest_income_account.update_balance_from_journals()
            
            # Late Fee Income Account
            config.late_fee_income_account.update_balance_from_journals()
            
            # Note: General Loans Receivable Account is NOT reset as per requirement
        
        messages.success(
            request,
            f'✅ Successfully reset {journal_count} split approvals. '
            f'GL account balances have been recalculated. '
            f'All payments are now ready for re-approval.'
        )
        
    except Exception as e:
        messages.error(request, f'Error resetting split approvals: {str(e)}')
    
    return redirect('loan_reconciliation_bridge:setup_gl_configuration')
