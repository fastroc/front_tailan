from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # Company management
    path('', views.company_list, name='company_list'),
    path('create/', views.company_create, name='company_create'),
    path('<int:company_id>/', views.company_detail, name='company_detail'),
    path('<int:company_id>/settings/', views.company_settings, name='company_settings'),
    path('<int:company_id>/delete/', views.company_delete, name='company_delete'),
    
    # API endpoints
    path('switch/', views.company_switch, name='company_switch'),
]
