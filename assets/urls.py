"""
Assets URLs
URL patterns for fixed asset management
"""

from django.urls import path
from . import views
from . import views_reports

app_name = 'assets'

urlpatterns = [
    # Asset management
    path('', views.assets_list, name='list'),
    path('new/', views.new_asset, name='new'),
    path('dashboard/', views.asset_dashboard, name='dashboard'),
    
    # Asset detail views
    path('<int:asset_id>/', views.asset_detail, name='detail'),
    path('<int:asset_id>/edit/', views.edit_asset, name='edit'),
    path('<int:asset_id>/delete/', views.delete_asset, name='delete'),
    path('<int:asset_id>/depreciation/', views.asset_depreciation, name='depreciation'),
    
    # Bulk operations
    path('bulk-delete/', views.bulk_delete_assets, name='bulk_delete'),
    
    # AJAX endpoints
    path('api/depreciation-preview/', views.calculate_depreciation_preview, name='depreciation_preview'),
    
    # Class-based views (when ready)
    path('cbv/list/', views.AssetListView.as_view(), name='cbv_list'),
    path('cbv/create/', views.AssetCreateView.as_view(), name='cbv_create'),
    path('cbv/<int:pk>/detail/', views.AssetDetailView.as_view(), name='cbv_detail'),
    path('cbv/<int:pk>/edit/', views.AssetUpdateView.as_view(), name='cbv_edit'),
    
    # ===== REPORTING SECTION =====
    path('reports/', views_reports.AssetReportsMenuView.as_view(), name='reports_menu'),
    
    # Financial Reports
    path('reports/balance-sheet/', views_reports.balance_sheet_assets_report, name='balance_sheet_report'),
    path('reports/trial-balance/', views_reports.trial_balance_assets_report, name='trial_balance_report'),
    path('reports/asset-register/', views_reports.asset_register_report, name='asset_register_report'),
    
    # Tax Reports
    path('reports/tax-schedule/', views_reports.tax_depreciation_schedule_report, name='tax_schedule_report'),
    path('reports/depreciation-expense/', views_reports.depreciation_expense_report, name='depreciation_expense_report'),
    path('reports/movements/', views_reports.asset_movements_report, name='movements_report'),
    
    # API Endpoints for Integration
    path('api/balance-sheet/', views_reports.api_balance_sheet_assets, name='api_balance_sheet'),
    path('api/trial-balance/', views_reports.api_trial_balance_assets, name='api_trial_balance'),
    
    # Export functionality
    path('reports/export/<str:report_type>/', views_reports.export_report, name='export_report'),
    
    # Operations
    path('run-depreciation/', views.run_depreciation_legacy, name='run_depreciation'),
    path('import/', views.import_assets, name='import'),
    path('export/', views.export_assets, name='export'),
]
