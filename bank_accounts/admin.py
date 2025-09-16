from django.contrib import admin
from .models import BankTransaction, UploadedFile


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'coa_account', 'company', 'description', 'amount', 'reference', 'uploaded_at', 'uploaded_by')
    list_filter = ('date', 'company', 'coa_account__company', 'coa_account__account_type', 'uploaded_at')
    search_fields = ('description', 'reference', 'coa_account__name', 'coa_account__code', 'company__name')
    date_hierarchy = 'date'
    readonly_fields = ('uploaded_at', 'uploaded_by')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('coa_account', 'company', 'uploaded_by')


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'account', 'company', 'uploaded_at', 'imported_count', 'duplicate_count', 'error_count', 'uploaded_by')
    list_filter = ('uploaded_at', 'company', 'account__company', 'account__name')
    search_fields = ('original_filename', 'account__name', 'account__code', 'company__name')
    readonly_fields = ('uploaded_at', 'file_hash', 'file_size')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account', 'company', 'uploaded_by')
