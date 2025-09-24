from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

# Import models
from assets.models import FixedAsset
from coa.models import Account
from journal.models import Journal
from bank_accounts.models import BankTransaction
from reconciliation.models import TransactionMatch
from company.models import Company


@login_required
def dashboard_view(request):
    """Reports Dashboard - Shows real accounting data"""
    
    # Get the active company from session or default to first company
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            company = Company.objects.first()
    else:
        company = Company.objects.first()
    
    if not company:
        # No company exists - show basic context
        context = {
            'company': None,
            'active_company': None,
            'error_message': 'No company found. Please create a company first.',
            'total_assets': Decimal('0.00'),
            'active_assets': 0,
            'active_accounts': 0,
            'total_accounts': 0,
            'posted_journals': 0,
            'draft_journals': 0,
            'total_journal_entries': 0,
            'total_bank_transactions': 0,
            'matched_transactions': 0,
            'pending_transactions': 0,
            'total_bank_balance': Decimal('0.00'),
            'reconciled_balance': Decimal('0.00'),
            'reconciliation_difference': Decimal('0.00'),
            'total_assets_balance': Decimal('0.00'),
            'total_liabilities': Decimal('0.00'),
        }
        return render(request, 'reports/dashboard.html', context)
    
    # Fixed Assets Data
    fixed_assets = FixedAsset.objects.filter(company=company)
    total_assets_cost = fixed_assets.aggregate(
        total=Sum('purchase_price')
    )['total'] or Decimal('0.00')
    
    active_assets_count = fixed_assets.filter(
        status='active'
    ).count()
    
    # Chart of Accounts Data
    all_accounts = Account.objects.filter(company=company)
    active_accounts_count = all_accounts.filter(is_active=True).count()
    
    # Bank Accounts specifically - only accounts marked as bank accounts
    bank_accounts = all_accounts.filter(is_bank_account=True)

    # Journal Entries Data (no company field, so get all)
    journals = Journal.objects.all()
    posted_journals_count = journals.filter(status='posted').count()
    draft_journals_count = journals.filter(status='draft').count()
    total_journal_entries = journals.count()
    
    # Bank Reconciliation Data
    bank_transactions = BankTransaction.objects.filter(
        coa_account__in=bank_accounts
    )
    total_bank_transactions = bank_transactions.count()
    
    # Matched transactions
    matched_transactions = TransactionMatch.objects.filter(
        bank_transaction__coa_account__in=bank_accounts,
        is_reconciled=True
    ).count()
    
    pending_transactions = total_bank_transactions - matched_transactions
    
    # Calculate bank balance difference
    total_bank_balance = bank_transactions.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    reconciled_balance = bank_transactions.filter(
        id__in=TransactionMatch.objects.filter(
            is_reconciled=True
        ).values_list('bank_transaction_id', flat=True)
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    reconciliation_difference = abs(total_bank_balance - reconciled_balance)
    
    # Calculate asset and liability balances (simplified)
    # This would normally come from journal line balances
    total_assets_balance = total_bank_balance + total_assets_cost
    
    # Sample liability calculation (you can enhance this)
    total_liabilities = total_assets_balance * Decimal('0.4')  # Simplified ratio
    
    # Prepare context with real data
    context = {
        'company': company,
        'active_company': company,
        
        # Fixed Assets metrics
        'total_assets': total_assets_cost,
        'active_assets': active_assets_count,
        
        # COA metrics
        'active_accounts': active_accounts_count,
        'total_accounts': all_accounts.count(),
        
        # Journal metrics
        'posted_journals': posted_journals_count,
        'draft_journals': draft_journals_count,
        'total_journal_entries': total_journal_entries,
        
        # Bank reconciliation metrics
        'total_bank_transactions': total_bank_transactions,
        'matched_transactions': matched_transactions,
        'pending_transactions': pending_transactions,
        'total_bank_balance': total_bank_balance,
        'reconciled_balance': reconciled_balance,
        'reconciliation_difference': reconciliation_difference,
        
        # Balance sheet metrics (simplified)
        'total_assets_balance': total_assets_balance,
        'total_liabilities': total_liabilities,
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
def journal_entries_view(request):
    """Journal Entries Report - Shows all journal entries with filtering"""
    
    # Get the active company from session or default to first company
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            company = Company.objects.first()
    else:
        company = Company.objects.first()
    
    # Get filter parameters from request
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset - Journal model doesn't have company field, so get all
    journals = Journal.objects.all().order_by('-date_created', '-id')
    
    # Apply status filter
    if status_filter != 'all':
        journals = journals.filter(status=status_filter)
    
    # Apply date filters
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            journals = journals.filter(date_created__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            journals = journals.filter(date_created__lte=date_to_obj)
        except ValueError:
            pass
    
    # Calculate summary statistics
    total_entries = journals.count()
    posted_count = journals.filter(status='posted').count()
    draft_count = journals.filter(status='draft').count()
    
    # Calculate total amounts (sum of debit amounts from journal lines)
    from journal.models import JournalLine
    journal_lines = JournalLine.objects.filter(journal__in=journals)
    total_debits = journal_lines.aggregate(
        total=Sum('debit_amount')
    )['total'] or Decimal('0.00')
    total_credits = journal_lines.aggregate(
        total=Sum('credit_amount')
    )['total'] or Decimal('0.00')
    
    context = {
        'company': company,
        'active_company': company,
        'journals': journals[:100],  # Limit to 100 for performance
        'total_entries': total_entries,
        'posted_count': posted_count,
        'draft_count': draft_count,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': [
            ('all', 'All Entries'),
            ('draft', 'Draft'),
            ('posted', 'Posted'),
        ]
    }
    
    return render(request, 'reports/journal_entries.html', context)


@login_required
def pending_reconciliation_view(request):
    """Pending Reconciliation Report - Shows unmatched transactions"""
    
    # Get the active company from session or default to first company
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            company = Company.objects.first()
    else:
        company = Company.objects.first()
    
    if not company:
        context = {
            'company': None,
            'active_company': None,
            'error_message': 'No company found. Please create a company first.',
            'pending_bank_transactions': [],
            'pending_journal_transactions': [],
            'total_pending_bank': 0,
            'total_pending_journal': 0,
            'total_unmatched_amount': Decimal('0.00'),
        }
        return render(request, 'reports/pending_reconciliation.html', context)
    
    # Get bank accounts for this company
    bank_accounts = Account.objects.filter(
        company=company,
        is_bank_account=True
    )
    
    # Get unmatched bank transactions
    # These are bank transactions that don't have a reconciliation match
    matched_bank_transaction_ids = TransactionMatch.objects.filter(
        is_reconciled=True
    ).values_list('bank_transaction_id', flat=True)
    
    pending_bank_transactions = BankTransaction.objects.filter(
        coa_account__in=bank_accounts
    ).exclude(
        id__in=matched_bank_transaction_ids
    ).order_by('-transaction_date', '-id')
    
    # Get unmatched journal transactions
    # These are journal lines that could be matched but haven't been
    from journal.models import JournalLine
    matched_journal_line_ids = TransactionMatch.objects.filter(
        is_reconciled=True,
        journal_line__isnull=False
    ).values_list('journal_line_id', flat=True)
    
    pending_journal_transactions = JournalLine.objects.filter(
        account__in=bank_accounts,
        journal__status='posted'
    ).exclude(
        id__in=matched_journal_line_ids
    ).order_by('-journal__date_created', '-id')
    
    # Calculate summary statistics
    total_pending_bank = pending_bank_transactions.count()
    total_pending_journal = pending_journal_transactions.count()
    
    # Calculate unmatched amounts
    bank_unmatched_amount = pending_bank_transactions.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    journal_unmatched_amount = pending_journal_transactions.aggregate(
        debit_total=Sum('debit_amount'),
        credit_total=Sum('credit_amount')
    )
    journal_net_amount = (
        (journal_unmatched_amount['debit_total'] or Decimal('0.00')) -
        (journal_unmatched_amount['credit_total'] or Decimal('0.00'))
    )
    
    total_unmatched_amount = abs(bank_unmatched_amount - journal_net_amount)
    
    # Get account filter parameter
    account_filter = request.GET.get('account')
    if account_filter:
        try:
            account = Account.objects.get(id=account_filter, company=company)
            pending_bank_transactions = pending_bank_transactions.filter(
                coa_account=account
            )
            pending_journal_transactions = pending_journal_transactions.filter(
                account=account
            )
        except Account.DoesNotExist:
            pass
    
    context = {
        'company': company,
        'active_company': company,
        'pending_bank_transactions': pending_bank_transactions[:50],  # Limit for performance
        'pending_journal_transactions': pending_journal_transactions[:50],
        'total_pending_bank': total_pending_bank,
        'total_pending_journal': total_pending_journal,
        'bank_unmatched_amount': bank_unmatched_amount,
        'journal_net_amount': journal_net_amount,
        'total_unmatched_amount': total_unmatched_amount,
        'bank_accounts': bank_accounts,
        'account_filter': account_filter,
    }
    
    return render(request, 'reports/pending_reconciliation.html', context)