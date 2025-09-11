from django.urls import path
from . import views
from . import ajax_views

app_name = 'reconciliation'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/<str:account_id>/', views.account_reconciliation, name='account_reconciliation'),
    path('account/<int:account_id>/', views.account_reconciliation, name='account_detail'),
    
    # AJAX endpoints
    path('ajax/match-transaction/', ajax_views.match_transaction, name='match_transaction'),
    path('ajax/unmatch-transaction/', ajax_views.unmatch_transaction, name='unmatch_transaction'),
    path('ajax/restart-reconciliation/', ajax_views.restart_reconciliation, name='restart_reconciliation'),
    path('ajax/progress/<int:account_id>/', ajax_views.reconciliation_progress, name='reconciliation_progress'),
    path('ajax/unmatched/<int:account_id>/', ajax_views.get_unmatched_transactions, name='get_unmatched_transactions'),
]
