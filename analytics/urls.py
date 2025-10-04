"""
Analytics App URLs
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.analytics_dashboard, name='dashboard'),
    path('pattern/<int:pattern_id>/', views.pattern_detail, name='pattern_detail'),
    path('reset-ai/', views.reset_ai_data, name='reset_ai'),
]
