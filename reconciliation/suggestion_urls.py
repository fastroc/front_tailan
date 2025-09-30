"""
Smart Suggestion API URLs

URL configuration for the smart suggestion system API endpoints.
"""

from django.urls import path
from . import suggestion_api_views

app_name = 'suggestion_api'

urlpatterns = [
    # Main suggestion endpoints
    path('suggestions/', 
         suggestion_api_views.suggestions_view, 
         name='suggestions'),
    
    path('quick-suggestions/', 
         suggestion_api_views.quick_suggestions_view, 
         name='quick_suggestions'),
    
    path('suggestions/details/', 
         suggestion_api_views.suggestion_details_view, 
         name='suggestion_details'),
    
    # Feedback and learning
    path('suggestion-feedback/', 
         suggestion_api_views.suggestion_feedback_view, 
         name='suggestion_feedback'),
    
    # Management and statistics
    path('service-stats/', 
         suggestion_api_views.service_stats_view, 
         name='service_stats'),
    
    path('clear-cache/', 
         suggestion_api_views.clear_cache_view, 
         name='clear_cache'),
    
    path('management/', 
         suggestion_api_views.SuggestionManagementView.as_view(), 
         name='management'),
    
    # Testing and development
    path('test/', 
         suggestion_api_views.test_suggestions_view, 
         name='test_suggestions'),
]
