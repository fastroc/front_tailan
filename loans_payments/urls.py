"""
URLs for loans_payments app - simplified version.
"""
from django.urls import path
from . import views

app_name = 'loans_payments'

urlpatterns = [
    # Simple Payments
    path('', views.payment_list, name='payment_list'),
    path('create/', views.payment_create, name='payment_create'),
    path('<int:pk>/', views.payment_detail, name='payment_detail'),
    path('<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('clear-all/', views.payments_clear_all, name='payments_clear_all'),
    
    # Bulk Payment Upload
    path('bulk-upload/', views.bulk_payment_upload, name='bulk_payment_upload'),
    path('bulk-upload/results/', views.bulk_payment_results, name='bulk_payment_results'),
    path('download-template/', views.download_payment_template, name='download_payment_template'),
    
    # Simple AJAX endpoint for loan search only
    path('api/loan-search/', views.loan_search, name='api_loan_search'),
    
    # Temporary endpoint to prevent template errors - returns empty response
    path('api/allocation-preview/', views.payment_allocation_preview, name='api_allocation_preview'),
    
    # Complex features - commented out for simplicity
    # path('quick-create/', views.payment_quick_create, name='payment_quick_create'),
    # path('auto-payments/', views.auto_payment_list, name='auto_payment_list'),
    # path('auto-payments/create/', views.auto_payment_create, name='auto_payment_create'),
    # path('auto-payments/<int:pk>/edit/', views.auto_payment_edit, name='auto_payment_edit'),
    # path('bulk-process/', views.bulk_payment_process, name='bulk_process'),
    # path('api/search/', views.payment_search, name='api_payment_search'),
]
