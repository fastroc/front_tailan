from django.urls import path
from . import views
from . import ajax_views
from . import ajax_split_views

app_name = 'reconciliation'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/<str:account_id>/', views.account_reconciliation, name='account_reconciliation'),
    path('account/<int:account_id>/', views.account_reconciliation, name='account_detail'),
    
    # AJAX endpoints
    path('ajax/match-transaction/', ajax_views.match_transaction, name='match_transaction'),
    path('ajax/unmatch-transaction/', ajax_views.unmatch_transaction, name='unmatch_transaction'),
    path('ajax/edit-match/<int:match_id>/', ajax_views.edit_transaction_match, name='edit_transaction_match'),
    path('ajax/get-match/<int:match_id>/', ajax_views.get_transaction_match, name='get_transaction_match'),
    path('ajax/matched/<int:account_id>/', ajax_views.get_matched_transactions, name='get_matched_transactions'),
    path('ajax/restart-reconciliation/', ajax_views.restart_reconciliation, name='restart_reconciliation'),
    path('ajax/progress/<int:account_id>/', ajax_views.reconciliation_progress, name='reconciliation_progress'),
    path('ajax/unmatched/<int:account_id>/', ajax_views.get_unmatched_transactions, name='get_unmatched_transactions'),
    
    # Split transaction AJAX endpoints
    path('ajax/split-transaction/create/', ajax_split_views.create_split_transaction, name='create_split_transaction'),
    path('ajax/split-transaction/<int:match_id>/details/', ajax_split_views.get_transaction_splits, name='get_transaction_splits'),
    path('ajax/split-transaction/validate/', ajax_split_views.validate_split_balance, name='validate_split_balance'),
    
    # Loan integration AJAX endpoints
    path('ajax/search-loan-customers/', ajax_views.search_loan_customers, name='search_loan_customers'),
    path('ajax/get-all-loan-customers/', ajax_views.get_all_loan_customers, name='get_all_loan_customers'),
    path('ajax/detect-loan-payment/<int:transaction_id>/', ajax_views.detect_loan_payment, name='detect_loan_payment'),
    path('ajax/create-loan-payment/', ajax_views.create_loan_payment_from_reconciliation, name='create_loan_payment'),
    path('ajax/get-loan-payment-breakdown/', ajax_views.get_loan_payment_breakdown, name='get_loan_payment_breakdown'),
    path('ajax/debug-loan-breakdown/', ajax_views.test_loan_breakdown_debug, name='debug_loan_breakdown'),
    path('ajax/debug-transaction/<int:transaction_id>/', ajax_views.debug_transaction, name='debug_transaction'),
    path('ajax/test-integration/', ajax_views.test_integration, name='test_integration'),
    path('ajax/test-search/', ajax_views.test_search_customers, name='test_search_customers'),
]
