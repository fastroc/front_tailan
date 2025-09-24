"""
URL patterns for Financial Rules - Web Interface and API endpoints
"""

from django.urls import path
from . import views

app_name = 'financial_rules'

urlpatterns = [
    # Web Interface URLs
    path('', views.RuleListView.as_view(), name='rule_list'),
    path('create/', views.RuleCreateView.as_view(), name='rule_create'),
    path('<int:pk>/', views.RuleDetailView.as_view(), name='rule_detail'),
    path('<int:pk>/edit/', views.RuleUpdateView.as_view(), name='rule_edit'),
    path('<int:pk>/delete/', views.RuleDeleteView.as_view(), name='rule_delete'),
    path('test/', views.TestRulesView.as_view(), name='test_rules'),
    
    # API endpoints (keeping existing functionality)
    path('api/evaluate/', views.EvaluateRulesView.as_view(), name='evaluate_rules'),
    path('api/test/<int:rule_id>/', views.TestRuleView.as_view(), name='test_rule'),
    path('api/rules/', views.get_available_rules, name='get_available_rules'),
    path('api/logs/', views.get_rule_execution_logs, name='get_rule_execution_logs'),
    path('api/auto_split/', views.auto_split_transaction, name='auto_split_transaction'),
    
    # Additional API endpoints for web interface
    path('api/evaluate_rules/', views.evaluate_rules, name='api_evaluate_rules'),
    path('api/test_rule/<int:rule_id>/', views.test_rule, name='api_test_rule'),
    path('api/toggle_rule/<int:rule_id>/', views.toggle_rule_status, name='api_toggle_rule'),
]
