"""
URL configuration for loan_reconciliation_bridge app
"""
from django.urls import path
from . import views

app_name = 'loan_reconciliation_bridge'

urlpatterns = [
    path('setup/', views.setup_gl_configuration, name='setup_gl_configuration'),
    path('reset-split-approvals/', views.reset_split_approvals, name='reset_split_approvals'),
    # Payment approval URLs removed - migrated to loan progress engine approach
]
