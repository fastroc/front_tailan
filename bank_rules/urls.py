"""
Bank Rules URL Configuration
-----------------------------
Routes for rule management interface.
"""

from django.urls import path
from . import views

app_name = 'bank_rules'

urlpatterns = [
    # Rule management
    path('', views.list_rules, name='list'),
    path('create/', views.create_rule, name='create'),
    path('<int:rule_id>/edit/', views.edit_rule, name='edit'),
    path('<int:rule_id>/delete/', views.delete_rule, name='delete'),
    path('<int:rule_id>/toggle/', views.toggle_rule, name='toggle'),
    
    # Testing
    path('<int:rule_id>/test/', views.test_rule, name='test'),
]
