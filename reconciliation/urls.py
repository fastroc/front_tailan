from django.urls import path
from .views import upload_csv, process_file, file_list, file_detail, health_check, showcase, transaction_detail

app_name = 'reconciliation'

urlpatterns = [
    path('', file_list, name='file_list'),
    path('', file_list, name='dashboard'),  # Add dashboard alias
    path('showcase/', showcase, name='showcase'),
    path('transaction/<int:transaction_id>/', transaction_detail, name='transaction_detail'),
    path('upload/', upload_csv, name='upload_csv'),
    path('process/<int:file_id>/', process_file, name='process_file'),
    path('file/<int:file_id>/', file_detail, name='file_detail'),
    path('health/', health_check, name='health_check'),
]