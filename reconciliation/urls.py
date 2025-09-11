from django.urls import path
from . import views

app_name = 'reconciliation'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/<str:account_id>/', views.account_reconciliation, name='account_reconciliation'),
    path('account/<int:account_id>/', views.account_reconciliation, name='account_detail'),
]
