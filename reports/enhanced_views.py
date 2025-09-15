"""
Enhanced Xero-Style Reports Views
Professional accounting reports with Xero-like styling and functionality
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime, timedelta
from decimal import Decimal

from company.models import Company
from coa.models import Account
from journal.models import Journal, JournalLine
from assets.models import FixedAsset


@login_required
def xero_style_dashboard(request):
    """Xero-style comprehensive dashboard with all reports"""
    
    # Get active company
    company = get_active_company(request)
    if not company:
        return render(request, 'reports/xero_dashboard.html', {'error': 'No company found'})
    
    # Date parameters
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    end_of_month = get_end_of_month(today)
    start_of_year = today.replace(month=1, day=1)
    
    # Generate comprehensive dashboard data
    dashboard_data = {
        'company': company,
        'report_date': today,
        'period': {
            'start_of_month': start_of_month,
            'end_of_month': end_of_month,
            'start_of_year': start_of_year,
            'current_month': today.strftime('%B %Y'),
            'current_year': today.year,
        },
        
        # Key Financial Metrics
        'key_metrics': get_key_financial_metrics(company, today),
        
        # Balance Sheet Summary
        'balance_sheet': get_balance_sheet_summary(company, today),
        
        # Profit & Loss Summary
        'profit_loss': get_profit_loss_summary(company, start_of_year, today),
        
        # Cash Flow Summary
        'cash_flow': get_cash_flow_summary(company, start_of_month, end_of_month),
        
        # Fixed Assets Summary
        'fixed_assets': get_fixed_assets_summary(company, today),
        
        # Bank Reconciliation Summary
        'bank_reconciliation': get_bank_reconciliation_summary(company),
        
        # Journal Entries Summary
        'journal_summary': get_journal_summary(company, start_of_month, end_of_month),
        
        # Outstanding Items
        'outstanding_items': get_outstanding_items(company),
        
        # Recent Activity
        'recent_activity': get_recent_activity(company, 7),  # Last 7 days
    }
    
    return render(request, 'reports/xero_dashboard.html', dashboard_data)


@login_required
def balance_sheet_report(request):
    """Professional Balance Sheet Report - Xero Style"""
    
    company = get_active_company(request)
    if not company:
        return JsonResponse({'error': 'No company found'})
    
    # Get report date
    report_date_str = request.GET.get('as_of_date')
    if report_date_str:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.now().date()
    
    # Generate balance sheet data
    balance_sheet_data = generate_full_balance_sheet(company, report_date)
    
    context = {
        'company': company,
        'report_date': report_date,
        'balance_sheet': balance_sheet_data,
        'report_title': 'Balance Sheet',
        'report_subtitle': f'As at {report_date.strftime("%B %d, %Y")}',
    }
    
    return render(request, 'reports/balance_sheet.html', context)


@login_required
def profit_loss_report(request):
    """Professional Profit & Loss Report - Xero Style"""
    
    company = get_active_company(request)
    if not company:
        return JsonResponse({'error': 'No company found'})
    
    # Get date range
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        # Default to current year
        today = timezone.now().date()
        start_date = today.replace(month=1, day=1)
        end_date = today
    
    # Generate P&L data
    pl_data = generate_profit_loss(company, start_date, end_date)
    
    context = {
        'company': company,
        'start_date': start_date,
        'end_date': end_date,
        'profit_loss': pl_data,
        'report_title': 'Profit and Loss',
        'report_subtitle': f'{start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}',
        'period_months': (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1,
    }
    
    return render(request, 'reports/profit_loss.html', context)


@login_required
def trial_balance_report(request):
    """Enhanced Trial Balance Report - All Accounts"""
    
    company = get_active_company(request)
    if not company:
        return JsonResponse({'error': 'No company found'})
    
    # Get report date
    report_date_str = request.GET.get('as_of_date')
    if report_date_str:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.now().date()
    
    # Generate trial balance
    trial_balance_data = generate_trial_balance(company, report_date)
    
    context = {
        'company': company,
        'report_date': report_date,
        'trial_balance': trial_balance_data,
        'report_title': 'Trial Balance',
        'report_subtitle': f'As at {report_date.strftime("%B %d, %Y")}',
    }
    
    return render(request, 'reports/trial_balance.html', context)


# Helper Functions

def get_active_company(request):
    """Get the active company from session or default"""
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            return Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            pass
    return Company.objects.first()


def get_end_of_month(date_obj):
    """Get the last day of the month for given date"""
    if date_obj.month == 12:
        return date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        return date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(days=1)


def get_key_financial_metrics(company, as_of_date):
    """Calculate key financial metrics for dashboard"""
    
    # Get all accounts for the company
    accounts = Account.objects.filter(company=company)
    
    # Calculate account balances from journal entries
    account_balances = {}
    for account in accounts:
        balance = calculate_account_balance(account, as_of_date)
        account_balances[account.code] = {
            'account': account,
            'balance': balance,
            'debit_balance': balance if balance >= 0 else Decimal('0'),
            'credit_balance': abs(balance) if balance < 0 else Decimal('0'),
        }
    
    # Calculate key metrics
    total_assets = sum(
        data['debit_balance'] for code, data in account_balances.items()
        if data['account'].account_type in ['CURRENT_ASSET', 'FIXED_ASSET', 'NON_CURRENT_ASSET']
    )
    
    total_liabilities = sum(
        data['credit_balance'] for code, data in account_balances.items()
        if data['account'].account_type in ['CURRENT_LIABILITY', 'LIABILITY', 'NON_CURRENT_LIABILITY']
    )
    
    total_equity = sum(
        data['credit_balance'] for code, data in account_balances.items()
        if data['account'].account_type == 'EQUITY'
    )
    
    # Revenue and Expenses (for current year)
    total_revenue = sum(
        data['credit_balance'] for code, data in account_balances.items()
        if data['account'].account_type in ['REVENUE', 'SALES', 'OTHER_INCOME']
    )
    
    total_expenses = sum(
        data['debit_balance'] for code, data in account_balances.items()
        if data['account'].account_type in ['EXPENSE', 'DEPRECIATION', 'DIRECT_COST', 'OVERHEAD']
    )
    
    net_profit = total_revenue - total_expenses
    
    # Cash accounts
    cash_accounts = accounts.filter(account_type='CURRENT_ASSET', name__icontains='cash')
    total_cash = sum(
        account_balances.get(acc.code, {}).get('debit_balance', Decimal('0'))
        for acc in cash_accounts
    )
    
    return {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'net_worth': total_assets - total_liabilities,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'total_cash': total_cash,
        'profit_margin': (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0'),
    }


def calculate_account_balance(account, as_of_date):
    """Calculate account balance up to a specific date from journal entries only
    
    Note: Bank transactions should be journalized before appearing on financial statements.
    This ensures proper double-entry bookkeeping and balanced financial reports.
    """
    
    # Get all journal lines for this account up to the date
    journal_lines = JournalLine.objects.filter(
        account_code=account.code,
        journal__date__lte=as_of_date,
        journal__status='posted'
    ).aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    total_debit = journal_lines['total_debit'] or Decimal('0')
    total_credit = journal_lines['total_credit'] or Decimal('0')
    
    # Calculate balance based on account type (proper double-entry accounting)
    if account.account_type in ['CURRENT_ASSET', 'FIXED_ASSET', 'NON_CURRENT_ASSET', 'EXPENSE', 'DEPRECIATION', 'DIRECT_COST', 'OVERHEAD']:
        # Debit accounts: Debit increases, Credit decreases
        return total_debit - total_credit
    else:
        # Credit accounts: Credit increases, Debit decreases
        return total_credit - total_debit


def generate_full_balance_sheet(company, as_of_date):
    """Generate complete balance sheet data"""
    
    accounts = Account.objects.filter(company=company).order_by('code')
    
    # Group accounts by type
    assets = {
        'current_assets': [],
        'fixed_assets': [],
        'other_assets': [],
    }
    
    liabilities = {
        'current_liabilities': [],
        'long_term_liabilities': [],
    }
    
    equity = []
    
    # Calculate balances and categorize
    for account in accounts:
        balance = calculate_account_balance(account, as_of_date)
        
        account_data = {
            'account': account,
            'balance': balance,
            'absolute_balance': abs(balance),
        }
        
        if account.account_type == 'CURRENT_ASSET':
            assets['current_assets'].append(account_data)
        elif account.account_type == 'FIXED_ASSET':
            assets['fixed_assets'].append(account_data)
        elif account.account_type == 'NON_CURRENT_ASSET':
            assets['other_assets'].append(account_data)
        elif account.account_type == 'CURRENT_LIABILITY':
            liabilities['current_liabilities'].append(account_data)
        elif account.account_type in ['LIABILITY', 'NON_CURRENT_LIABILITY']:
            liabilities['long_term_liabilities'].append(account_data)
        elif account.account_type == 'EQUITY':
            equity.append(account_data)
    
    # Calculate totals
    total_current_assets = sum(acc['balance'] for acc in assets['current_assets'])
    total_fixed_assets = sum(acc['balance'] for acc in assets['fixed_assets'])
    total_other_assets = sum(acc['balance'] for acc in assets['other_assets'])
    total_assets = total_current_assets + total_fixed_assets + total_other_assets
    
    total_current_liabilities = sum(abs(acc['balance']) for acc in liabilities['current_liabilities'])
    total_long_term_liabilities = sum(abs(acc['balance']) for acc in liabilities['long_term_liabilities'])
    total_liabilities = total_current_liabilities + total_long_term_liabilities
    
    total_equity = sum(abs(acc['balance']) for acc in equity)
    
    return {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'totals': {
            'current_assets': total_current_assets,
            'fixed_assets': total_fixed_assets,
            'other_assets': total_other_assets,
            'total_assets': total_assets,
            'current_liabilities': total_current_liabilities,
            'long_term_liabilities': total_long_term_liabilities,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_liabilities_equity': total_liabilities + total_equity,
            'balance_check': total_assets - (total_liabilities + total_equity),
        }
    }


def generate_profit_loss(company, start_date, end_date):
    """Generate profit and loss statement data"""
    
    accounts = Account.objects.filter(company=company).order_by('code')
    
    revenue_accounts = []
    expense_accounts = []
    
    # Get revenue and expense accounts with period balances
    for account in accounts:
        period_balance = calculate_period_balance(account, start_date, end_date)
        
        if period_balance != 0:
            account_data = {
                'account': account,
                'balance': abs(period_balance),
            }
            
            if account.account_type in ['REVENUE', 'SALES', 'OTHER_INCOME']:
                revenue_accounts.append(account_data)
            elif account.account_type in ['EXPENSE', 'DEPRECIATION', 'DIRECT_COST', 'OVERHEAD']:
                expense_accounts.append(account_data)
    
    # Calculate totals
    total_revenue = sum(acc['balance'] for acc in revenue_accounts)
    total_expenses = sum(acc['balance'] for acc in expense_accounts)
    gross_profit = total_revenue
    net_profit = total_revenue - total_expenses
    
    return {
        'revenue_accounts': revenue_accounts,
        'expense_accounts': expense_accounts,
        'totals': {
            'total_revenue': total_revenue,
            'gross_profit': gross_profit,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0'),
        }
    }


def calculate_period_balance(account, start_date, end_date):
    """Calculate account balance for a specific period"""
    
    journal_lines = JournalLine.objects.filter(
        account_code=account.code,
        journal__date__gte=start_date,
        journal__date__lte=end_date,
        journal__status='posted'
    ).aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    total_debit = journal_lines['total_debit'] or Decimal('0')
    total_credit = journal_lines['total_credit'] or Decimal('0')
    
    if account.account_type in ['REVENUE', 'SALES', 'OTHER_INCOME']:
        return total_credit - total_debit
    elif account.account_type in ['EXPENSE', 'DEPRECIATION', 'DIRECT_COST', 'OVERHEAD']:
        return total_debit - total_credit
    else:
        return total_debit - total_credit


def generate_trial_balance(company, as_of_date):
    """Generate trial balance for all accounts"""
    
    accounts = Account.objects.filter(company=company, is_active=True).order_by('code')
    
    trial_balance_accounts = []
    total_debits = Decimal('0')
    total_credits = Decimal('0')
    
    for account in accounts:
        balance = calculate_account_balance(account, as_of_date)
        
        if balance != 0:  # Only include accounts with balances
            debit_amount = balance if balance > 0 else Decimal('0')
            credit_amount = abs(balance) if balance < 0 else Decimal('0')
            
            trial_balance_accounts.append({
                'account': account,
                'balance': balance,
                'debit_amount': debit_amount,
                'credit_amount': credit_amount,
            })
            
            total_debits += debit_amount
            total_credits += credit_amount
    
    return {
        'accounts': trial_balance_accounts,
        'totals': {
            'total_debits': total_debits,
            'total_credits': total_credits,
            'difference': total_debits - total_credits,
            'is_balanced': abs(total_debits - total_credits) < Decimal('0.01'),
        }
    }


def get_balance_sheet_summary(company, as_of_date):
    """Get summarized balance sheet data for dashboard"""
    balance_sheet = generate_full_balance_sheet(company, as_of_date)
    return {
        'total_assets': balance_sheet['totals']['total_assets'],
        'total_liabilities': balance_sheet['totals']['total_liabilities'],
        'total_equity': balance_sheet['totals']['total_equity'],
        'net_worth': balance_sheet['totals']['total_assets'] - balance_sheet['totals']['total_liabilities'],
    }


def get_profit_loss_summary(company, start_date, end_date):
    """Get summarized P&L data for dashboard"""
    pl_data = generate_profit_loss(company, start_date, end_date)
    return pl_data['totals']


def get_cash_flow_summary(company, start_date, end_date):
    """Get cash flow summary for dashboard"""
    # This is a simplified cash flow - in real implementation,
    # you'd calculate operating, investing, and financing activities
    
    cash_accounts = Account.objects.filter(
        company=company,
        account_type='CURRENT_ASSET',
        name__icontains='cash'
    )
    
    opening_balance = Decimal('0')
    closing_balance = Decimal('0')
    
    for account in cash_accounts:
        opening_balance += calculate_account_balance(account, start_date - timedelta(days=1))
        closing_balance += calculate_account_balance(account, end_date)
    
    net_change = closing_balance - opening_balance
    
    return {
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
        'net_change': net_change,
        'cash_flow_positive': net_change >= 0,
    }


def get_fixed_assets_summary(company, as_of_date):
    """Get fixed assets summary for dashboard"""
    
    assets = FixedAsset.objects.filter(company=company)
    
    total_cost = assets.aggregate(Sum('purchase_price'))['purchase_price__sum'] or Decimal('0')
    
    # Calculate accumulated depreciation based on existing fields
    total_depreciation = Decimal('0')
    for asset in assets:
        if asset.purchase_price and asset.depreciation_rate:
            # Simple calculation: (purchase_price * depreciation_rate / 100) * years_since_purchase
            years_since_purchase = (as_of_date - asset.purchase_date).days / 365.25 if asset.purchase_date else 0
            asset_depreciation = asset.purchase_price * (asset.depreciation_rate / 100) * Decimal(str(years_since_purchase))
            # Cap at purchase price minus residual value
            max_depreciation = asset.purchase_price - (asset.residual_value or Decimal('0'))
            total_depreciation += min(asset_depreciation, max_depreciation)
    
    net_book_value = total_cost - total_depreciation
    
    return {
        'total_assets': assets.count(),
        'active_assets': assets.filter(status='active').count(),
        'total_cost': total_cost,
        'accumulated_depreciation': total_depreciation,
        'net_book_value': net_book_value,
    }


def get_bank_reconciliation_summary(company):
    """Get bank reconciliation summary for dashboard"""
    
    # Simplified version without BankTransaction dependency
    return {
        'total_transactions': 0,
        'matched_transactions': 0,
        'pending_transactions': 0,
        'reconciliation_rate': 0,
    }


def get_journal_summary(company, start_date, end_date):
    """Get journal entries summary for dashboard"""
    
    journals = Journal.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    return {
        'total_journals': journals.count(),
        'posted_journals': journals.filter(status='posted').count(),
        'draft_journals': journals.filter(status='draft').count(),
        'total_amount': journals.filter(status='posted').aggregate(
            Sum('lines__debit')
        )['lines__debit__sum'] or Decimal('0'),
    }


def get_outstanding_items(company):
    """Get outstanding items that need attention"""
    
    outstanding = {
        'unbalanced_journals': Journal.objects.filter(status='draft').count(),
        'pending_reconciliation': get_bank_reconciliation_summary(company)['pending_transactions'],
        'inactive_accounts': Account.objects.filter(company=company, is_active=False).count(),
    }
    
    return outstanding


def get_recent_activity(company, days=7):
    """Get recent activity for dashboard"""
    
    since_date = timezone.now().date() - timedelta(days=days)
    
    recent_journals = Journal.objects.filter(
        date__gte=since_date
    ).order_by('-date')[:5]
    
    recent_assets = FixedAsset.objects.filter(
        company=company,
        purchase_date__gte=since_date
    ).order_by('-purchase_date')[:3]
    
    return {
        'recent_journals': recent_journals,
        'recent_assets': recent_assets,
        'period_days': days,
    }
