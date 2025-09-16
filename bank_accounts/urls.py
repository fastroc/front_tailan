from django.urls import path
from . import views

app_name = 'bank_accounts'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_account, name='add'),
    path('<int:account_id>/statement/', views.bank_statement, name='bank_statement'),
    path('upload/<int:account_id>/', views.upload_transactions, name='upload_transactions'),
    path('upload/<int:account_id>/delete/<int:upload_id>/', views.delete_upload, name='delete_upload'),
]
