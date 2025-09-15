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
]
