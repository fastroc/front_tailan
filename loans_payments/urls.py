"""
URLs for loans_payments app.
"""
from django.urls import path
from . import views

app_name = 'loans_payments'

urlpatterns = [
    # Payments
    path('', views.payment_list, name='payment_list'),
    path('create/', views.payment_create, name='payment_create'),
    path('quick-create/', views.payment_quick_create, name='payment_quick_create'),
    path('<int:pk>/', views.payment_detail, name='payment_detail'),
    
    # Auto Payments
    path('auto-payments/', views.auto_payment_list, name='auto_payment_list'),
    path('auto-payments/create/', views.auto_payment_create, name='auto_payment_create'),
    path('auto-payments/<int:pk>/edit/', views.auto_payment_edit, name='auto_payment_edit'),
    
    # Bulk Operations
    path('bulk-process/', views.bulk_payment_process, name='bulk_process'),
    
    # AJAX endpoints
    path('api/search/', views.payment_search, name='api_payment_search'),
]
