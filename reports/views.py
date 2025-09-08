from django.shortcuts import render


def dashboard_view(request):
    """Reports dashboard with sample data"""
    context = {
        'total_assets': 125750,
        'active_accounts': 47,
        'journal_entries': 23,
        'pending_reconciliation': 12,
        
        # Bank reconciliation data
        'matched_transactions': 89,
        'pending_transactions': 12,
        'reconciliation_difference': 2340,
        
        # Journal data
        'posted_journals': 18,
        'draft_journals': 5,
        'total_journal_amount': 45890,
        
        # Account balances
        'total_assets_balance': 89450,
        'total_liabilities': 36300,
    }
    
    return render(request, 'reports/dashboard.html', context)
