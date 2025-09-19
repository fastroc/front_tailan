"""
URLs for loans_core app.
"""
from django.urls import path
from . import views

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
    path('applications/<int:pk>/', views.loan_application_detail, name='application_detail'),
    path('applications/<int:pk>/approve/', views.loan_application_approve, name='application_approve'),
    
    # Loans
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:pk>/disburse/', views.loan_disburse, name='loan_disburse'),
    
    # Reports
    path('reports/', views.loan_reports, name='reports'),
    
    # AJAX endpoints
    path('api/product/<int:pk>/details/', views.get_loan_product_details, name='api_product_details'),
    path('api/calculate-payment/', views.calculate_loan_payment, name='api_calculate_payment'),
    
    # Legacy showcase URLs (redirects)
    path('showcase/dashboard/', views.showcase_dashboard, name='showcase_dashboard'),
    path('showcase/applications/', views.showcase_applications, name='showcase_applications'),
    path('showcase/customers/', views.showcase_customers, name='showcase_customers'),
    path('showcase/payments/', views.showcase_payments, name='showcase_payments'),
    path('showcase/reports/', views.showcase_reports, name='showcase_reports'),
]
