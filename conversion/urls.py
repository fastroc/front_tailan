from django.urls import path
from . import views

app_name = 'conversion'

urlpatterns = [
    # Conversion date setup
    path('date/<int:company_id>/', views.conversion_date_view, name='date'),
    
    # Conversion balances
    path('balances/<int:company_id>/', views.conversion_balances_view, name='balances'),
    
    # Comparative balances
    path('comparatives/<int:company_id>/', views.conversion_comparatives_view, name='comparatives'),
    
    # API endpoints
    path('api/save-balances/<int:company_id>/', views.save_conversion_balances, name='save_balances'),
]
