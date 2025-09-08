from django.urls import path
from . import views_demo as views  # DEMO VIEWS FOR FRONTEND SHOWCASE

app_name = 'company'

urlpatterns = [
    # Company management
    path('', views.company_list, name='company_list'),
    path('create/', views.company_create, name='company_create'),
    path('<uuid:company_id>/', views.company_detail, name='company_detail'),
    path('<uuid:company_id>/settings/', views.company_settings, name='company_settings'),
    
    # API endpoints
    path('switch/<uuid:company_id>/', views.company_switch, name='company_switch'),
]
