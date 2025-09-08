from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('reports/', views.reports_dashboard_view, name='reports_dashboard'),
    path('test-404/', views.test_404_view, name='test_404'),
    path('test-500/', views.test_500_view, name='test_500'),
    path('template-showcase/', views.template_showcase, name='template_showcase'),
]
