"""
URLs for loans_core app.
"""
from django.urls import path
from . import views, api_views

app_name = 'loans_core'

urlpatterns = [
    # Main dashboard
    path('', views.loan_dashboard, name='dashboard'),
    
    # Loan Products
    path('products/', views.loan_product_list, name='product_list'),
    path('products/create/', views.loan_product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.loan_product_edit, name='product_edit'),
    
    # Loan Applications
    path('applications/', views.loan_application_list, name='application_list'),
    path('applications/create/', views.loan_application_create, name='application_create'),
    path('applications/bulk-upload/', views.loan_application_bulk_upload, name='application_bulk_upload'),
    path('applications/bulk-upload/template/', views.download_loan_application_template, name='application_template_download'),
    path('applications/bulk-upload/review/', views.bulk_upload_review, name='bulk_upload_review'),
    path('applications/<int:pk>/', views.loan_application_detail, name='application_detail'),
    path('applications/<int:pk>/approve/', views.loan_application_approve, name='application_approve'),
    path('applications/<int:pk>/delete/', views.loan_application_delete, name='application_delete'),
    path('applications/<int:pk>/quick-action/', views.application_quick_action, name='application_quick_action'),
    path('applications/<int:pk>/progress/', views.application_progress, name='application_progress'),
    
    # Payment Approval Endpoints (Loan Progress Engine)
    path('applications/<int:pk>/approve-payment/', views.approve_payment, name='approve_payment'),
    path('applications/<int:pk>/edit-payment-allocation/', views.edit_payment_allocation, name='edit_payment_allocation'),
    path('applications/<int:pk>/approve-entire-loan/', views.approve_entire_loan, name='approve_entire_loan'),
    
    # Loans
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:pk>/disburse/', views.loan_disburse, name='loan_disburse'),
    
    # Reports
    path('reports/', views.loan_reports, name='reports'),
    
    # AJAX endpoints
    path('api/product/<int:pk>/details/', views.get_loan_product_details, name='api_product_details'),
    path('api/calculate-payment/', views.calculate_loan_payment, name='api_calculate_payment'),
    
    # Phase 3 Advanced API endpoints for lazy loading and real-time updates
    path('api/applications/<int:application_id>/progress/', api_views.application_progress_api, name='api_application_progress'),
    path('api/debug/applications/<int:application_id>/progress/', api_views.debug_progress_api, name='debug_application_progress'),
    path('api/applications/batch-progress/', api_views.batch_progress_api, name='api_batch_progress'),
    path('api/applications/list/', api_views.applications_list_api, name='api_applications_list'),
    path('api/applications/<int:application_id>/update-progress/', api_views.ApplicationProgressUpdateView.as_view(), name='api_update_progress'),
    path('api/system/performance/', api_views.system_performance_api, name='api_system_performance'),
    path('api/cache/warm/', api_views.cache_warm_api, name='api_cache_warm'),
    path('api/dashboard/', api_views.progress_dashboard_api, name='api_progress_dashboard'),
    
    # Debug/Test endpoints
    path('test/dropdown/', views.dropdown_test, name='dropdown_test'),
    
    # Legacy showcase URLs (redirects)
    path('showcase/dashboard/', views.showcase_dashboard, name='showcase_dashboard'),
    path('showcase/applications/', views.showcase_applications, name='showcase_applications'),
    path('showcase/customers/', views.showcase_customers, name='showcase_customers'),
    path('showcase/payments/', views.showcase_payments, name='showcase_payments'),
    path('showcase/reports/', views.showcase_reports, name='showcase_reports'),
]
