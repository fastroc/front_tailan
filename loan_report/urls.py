from django.urls import path
from . import views

app_name = 'loan_report'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # API endpoints for dynamic data
    path('api/portfolio/', views.api_portfolio_data, name='api_portfolio'),
    path('api/monthly-trends/', views.api_monthly_trends, name='api_monthly_trends'),
    path('api/aging-analysis/', views.api_aging_analysis, name='api_aging_analysis'),
    
    # Export and configuration
    path('export/', views.export_report, name='export_report'),
    path('save-config/', views.save_report_config, name='save_config'),
    path('refresh-cache/', views.refresh_cache, name='refresh_cache'),
]
