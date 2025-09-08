from django.contrib import admin
from django.utils.html import format_html
from .models import Account, TaxRate


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    """Admin interface for Tax Rates"""
    list_display = ('name', 'percentage_display', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Tax Rate Information', {
            'fields': ('name', 'rate', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """Admin interface for Chart of Accounts"""
    list_display = (
        'code', 
        'name', 
        'account_type', 
        'tax_rate_display_admin',
        'formatted_ytd_balance', 
        'lock_status_display', 
        'is_active'
    )
    list_filter = ('account_type', 'is_locked', 'is_active', 'tax_rate')
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('code', 'name', 'account_type', 'description')
        }),
        ('Financial Settings', {
            'fields': ('tax_rate', 'ytd_balance')
        }),
        ('Account Control', {
            'fields': ('is_locked', 'is_active', 'parent_account')
        }),
        ('Audit Trail', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def tax_rate_display_admin(self, obj):
        """Display tax rate with percentage"""
        return f"{obj.tax_rate.name} ({obj.tax_rate.rate * 100:.2f}%)"
    tax_rate_display_admin.short_description = 'Tax Rate'
    
    def formatted_ytd_balance(self, obj):
        """Display YTD balance with color coding"""
        color = 'green' if obj.ytd_balance >= 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span>',
            color,
            f"{obj.ytd_balance:,.2f}"
        )
    formatted_ytd_balance.short_description = 'YTD Balance'
    formatted_ytd_balance.admin_order_field = 'ytd_balance'
    
    def lock_status_display(self, obj):
        """Display lock status with icons"""
        if obj.is_locked:
            return format_html('<span style="color: red;">🔒 Locked</span>')
        return format_html('<span style="color: green;">🔓 Unlocked</span>')
    lock_status_display.short_description = 'Lock Status'
    lock_status_display.admin_order_field = 'is_locked'
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by and updated_by"""
        if not change:  # Creating new account
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queries by selecting related objects"""
        return super().get_queryset(request).select_related('tax_rate', 'parent_account')
