"""
URLs for loans_collateral app.
"""
from django.urls import path
from . import views

app_name = 'loans_collateral'

urlpatterns = [
    # Main collateral dashboard
    path('', views.collateral_dashboard, name='dashboard'),
    
    # Collateral Types
    path('types/', views.collateral_type_list, name='type_list'),
    path('types/create/', views.collateral_type_create, name='type_create'),
    path('types/<int:pk>/edit/', views.collateral_type_edit, name='type_edit'),
    path('types/<int:pk>/', views.collateral_type_detail, name='type_detail'),
    
    # Collateral Items
    path('items/', views.collateral_list, name='collateral_list'),
    path('items/create/', views.collateral_create, name='collateral_create'),
    path('items/create/debug/', views.collateral_create_debug, name='collateral_create_debug'),
    path('items/<int:pk>/', views.collateral_detail, name='collateral_detail'),
    path('items/<int:pk>/edit/', views.collateral_update, name='collateral_update'),
    path('items/<int:pk>/delete/', views.collateral_delete, name='collateral_delete'),
    path('items/bulk-delete/', views.collateral_bulk_delete, name='collateral_bulk_delete'),
    
    # Collateral for specific loan application
    path('application/<int:application_id>/', views.application_collateral_list, name='application_list'),
    path('application/<int:application_id>/add/', views.application_collateral_add, name='application_add'),
    
    # Valuations
    path('items/<int:collateral_id>/valuations/', views.collateral_valuation_list, name='valuation_list'),
    path('items/<int:collateral_id>/valuations/create/', views.collateral_valuation_create, name='valuation_create'),
    path('valuations/<int:pk>/', views.collateral_valuation_detail, name='valuation_detail'),
    path('valuations/<int:pk>/edit/', views.collateral_valuation_edit, name='valuation_edit'),
    
    # Documents
    path('items/<int:collateral_id>/documents/', views.collateral_document_list, name='document_list'),
    path('items/<int:collateral_id>/documents/upload/', views.collateral_document_upload, name='document_upload'),
    path('documents/<int:pk>/', views.collateral_document_detail, name='document_detail'),
    path('documents/<int:pk>/delete/', views.collateral_document_delete, name='document_delete'),
    
    # Actions
    path('items/<int:pk>/verify/', views.collateral_verify, name='verify'),
    path('items/<int:pk>/approve/', views.collateral_approve, name='approve'),
    path('items/<int:pk>/reject/', views.collateral_reject, name='reject'),
    path('items/<int:pk>/release/', views.collateral_release, name='release'),
    
    # API Endpoints
    path('api/type/<int:type_id>/', views.api_collateral_type_details, name='api_collateral_type_details'),
    path('api/items/<int:pk>/summary/', views.api_collateral_summary, name='api_summary'),
    path('api/calculate-ltv/', views.api_calculate_ltv, name='api_calculate_ltv'),
    path('api/search-loan-applications/', views.search_loan_applications, name='api_search_loan_applications'),
    path('api/check-duplicates/', views.api_check_duplicates, name='api_check_duplicates'),
    
    # Reports
    path('reports/', views.collateral_reports, name='reports'),
    path('reports/summary/', views.collateral_summary_report, name='summary_report'),
    path('reports/risk-analysis/', views.collateral_risk_report, name='risk_report'),
]
