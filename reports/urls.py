from django.urls import path
from . import views
from . import enhanced_views

app_name = 'reports'

urlpatterns = [
    # Original dashboard
    path('dashboard/', views.dashboard_view, name='reports_dashboard'),
    path('journal-entries/', views.journal_entries_view, name='reports_journal_entries'),
    path('pending-reconciliation/', views.pending_reconciliation_view, name='reports_pending_reconciliation'),
    
    # Xero-style enhanced reports
    path('', enhanced_views.xero_style_dashboard, name='xero_dashboard'),
    path('balance-sheet/', enhanced_views.balance_sheet_report, name='balance_sheet'),
    path('profit-loss/', enhanced_views.profit_loss_report, name='profit_loss'),
    path('trial-balance/', enhanced_views.trial_balance_report, name='trial_balance'),
]
