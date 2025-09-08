from django.urls import path
from . import views

app_name = 'coa'

urlpatterns = [
    path('', views.chart_of_accounts_view, name='chart_of_accounts'),
    path('account/<int:account_id>/', views.account_detail_view, name='account_detail'),
    path('account/create/', views.create_account_view, name='create_account'),
    path('api/account-search/', views.account_search_api, name='account_search_api'),
]
