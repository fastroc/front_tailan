"""
URLs for loans_schedule app.
"""
from django.urls import path
from . import views

app_name = 'loans_schedule'

urlpatterns = [
    # Payment Schedules
    path('', views.payment_schedule_list, name='schedule_list'),
    path('create/', views.payment_schedule_create, name='schedule_create'),
    path('generate/', views.payment_schedule_generate, name='schedule_generate'),
    path('<int:pk>/', views.payment_schedule_detail, name='schedule_detail'),
    path('<int:schedule_pk>/payments/<int:payment_pk>/edit/', views.scheduled_payment_edit, name='payment_edit'),
    path('<int:schedule_pk>/bulk-update/', views.bulk_payment_update, name='bulk_update'),
    
    # Custom Presets
    path('presets/', views.custom_preset_list, name='preset_list'),
    path('presets/create/', views.custom_preset_create, name='preset_create'),
    
    # Payment Date Rules
    path('rules/', views.payment_date_rule_list, name='rule_list'),
    path('rules/create/', views.payment_date_rule_create, name='rule_create'),
    
    # AJAX endpoints
    path('api/calculate/', views.calculate_payment_schedule, name='api_calculate'),
    path('api/<int:pk>/data/', views.get_payment_schedule_data, name='api_schedule_data'),
]
