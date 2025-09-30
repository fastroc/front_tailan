"""
URLs for loans_customers app.
"""
from django.urls import path
from . import views

app_name = 'loans_customers'

urlpatterns = [
    # Customer management
    path('', views.customer_list, name='customer_list'),
    path('create/', views.customer_create, name='customer_create'),
    path('quick-create/', views.customer_quick_create, name='customer_quick_create'),
    path('bulk-upload/', views.customer_bulk_upload, name='customer_bulk_upload'),
    path('<int:pk>/', views.customer_detail, name='customer_detail'),
    path('<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('<int:pk>/toggle-status/', views.customer_toggle_status, name='customer_toggle_status'),
    path('<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Customer documents
    path('<int:pk>/documents/', views.customer_documents, name='customer_documents'),
    path('<int:pk>/documents/upload/', views.customer_document_upload, name='customer_document_upload'),
    path('<int:customer_pk>/documents/<int:doc_pk>/review/', views.customer_document_review, name='customer_document_review'),
    
    # AJAX endpoints
    path('api/search/', views.customer_search, name='api_customer_search'),
]
