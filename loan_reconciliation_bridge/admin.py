"""
Admin configuration for loan_reconciliation_bridge app
"""
from django.contrib import admin
from .models import LoanGLConfiguration, LoanCalculationLog


@admin.register(LoanGLConfiguration)
class LoanGLConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Loan GL Configuration"""
    
    list_display = [
        'company',
        'principal_account',
        'interest_income_account',
        'late_fee_income_account',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['company__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company', {
            'fields': ('company',)
        }),
        ('GL Account Configuration', {
            'fields': ('principal_account', 'interest_income_account', 'late_fee_income_account'),
            'description': 'Configure the GL accounts used for loan payment allocations'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanCalculationLog)
class LoanCalculationLogAdmin(admin.ModelAdmin):
    """Admin interface for Loan Calculation Log"""
    
    list_display = [
        'customer_name',
        'payment_amount',
        'calculation_source',
        'success',
        'calculated_at'
    ]
    list_filter = ['calculation_source', 'success', 'company', 'calculated_at']
    search_fields = ['customer_name']
    readonly_fields = ['calculated_at']
    
    fieldsets = (
        ('Customer & Loan Info', {
            'fields': ('company', 'customer_name')
        }),
        ('Payment Breakdown', {
            'fields': ('payment_amount', 'late_fee_amount', 'interest_amount', 'principal_amount')
        }),
        ('Calculation Details', {
            'fields': ('calculation_source', 'success', 'error_message', 'calculated_at')
        }),
    )
