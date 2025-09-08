from django.contrib import admin
from .models import Company, UserCompanyRole, UserCompanyPreference

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'business_type', 'base_currency', 'is_active', 'created_at']
    list_filter = ['business_type', 'base_currency', 'is_active', 'country']
    search_fields = ['name', 'legal_name', 'email', 'registration_number', 'tax_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'legal_name', 'logo')
        }),
        ('Business Registration', {
            'fields': ('business_type', 'industry', 'registration_number', 'tax_id')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country')
        }),
        ('Financial Settings', {
            'fields': ('base_currency', 'financial_year_start')
        }),
        ('System Information', {
            'fields': ('id', 'is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserCompanyRole)
class UserCompanyRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'can_edit_settings', 'can_manage_users']
    search_fields = ['user__username', 'user__email', 'company__name']
    raw_id_fields = ['user', 'company']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'company', 'role')
        }),
        ('Permissions', {
            'fields': ('is_active', 'can_edit_settings', 'can_manage_users', 'can_view_reports')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

@admin.register(UserCompanyPreference)
class UserCompanyPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'active_company', 'default_company', 'updated_at']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user', 'active_company', 'default_company']
    readonly_fields = ['created_at', 'updated_at']
