from django.urls import path
from . import views

app_name = 'bank_accounts'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_account, name='add'),
    path('convert/', views.convert_account, name='convert'),
    path('<int:account_id>/statement/', views.bank_statement, name='bank_statement'),
    path('upload/<int:account_id>/', views.upload_transactions, name='upload_transactions'),
    path('upload/<int:account_id>/delete/<int:upload_id>/', views.delete_upload, name='delete_upload'),
    # Mongolian translation support
    path('enhanced-upload/<int:account_id>/', views.enhanced_upload, name='enhanced_upload'),
    path('translation-verification/<uuid:processing_id>/', views.translation_verification, name='translation_verification'),
    path('api/analyze-file/', views.analyze_file_preview, name='analyze_file_preview'),
    # Smart transaction processing with AI suggestions
    path('smart-processing/', views.smart_transaction_processing, name='smart_transaction_processing'),
]
