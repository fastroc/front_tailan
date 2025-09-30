from django.contrib import admin
from .models import CollateralType, Collateral, CollateralValuation, CollateralDocument

@admin.register(CollateralType)
class CollateralTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'risk_level', 'max_loan_to_value', 'is_active']
    list_filter = ['category', 'risk_level', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']

@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = [
        'collateral_id', 'title', 'get_customer_name', 'collateral_type', 
        'status', 'declared_value', 'market_value', 'created_at'
    ]
    list_filter = ['status', 'collateral_type', 'condition', 'created_at']
    search_fields = [
        'collateral_id', 'title', 'description', 'owner_name',
        'loan_application__customer__first_name',
        'loan_application__customer__last_name'
    ]
    readonly_fields = ['collateral_id', 'uuid', 'created_at', 'updated_at', 'loan_to_value_ratio']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('collateral_id', 'uuid', 'loan_application', 'collateral_type', 'title', 'description')
        }),
        ('Physical Details', {
            'fields': ('location', 'condition')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_make', 'vehicle_model', 'vehicle_year', 'vehicle_registration_year',
                      'vehicle_license_plate', 'vehicle_vin', 'vehicle_mileage', 'vehicle_fuel_type'),
            'classes': ('collapse',)
        }),
        ('Ownership', {
            'fields': ('owner_name', 'ownership_document', 'registration_number')
        }),
        ('Valuation', {
            'fields': ('declared_value', 'market_value', 'loan_value', 'loan_to_value_ratio')
        }),
        ('Status', {
            'fields': ('status', 'verification_date', 'verification_notes', 'verified_by')
        }),
        ('Insurance', {
            'fields': ('insurance_required', 'insurance_policy_number', 'insurance_expiry_date', 'insurance_value')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_customer_name(self, obj):
        if obj.loan_application and obj.loan_application.customer:
            return obj.loan_application.customer.get_full_name()
        return 'N/A'
    get_customer_name.short_description = 'Customer'

@admin.register(CollateralValuation)
class CollateralValuationAdmin(admin.ModelAdmin):
    list_display = [
        'collateral', 'valuation_type', 'valuer_name', 
        'assessed_value', 'valuation_date', 'is_current'
    ]
    list_filter = ['valuation_type', 'valuer_type', 'is_current', 'valuation_date']
    search_fields = ['collateral__collateral_id', 'valuer_name', 'report_reference']
    date_hierarchy = 'valuation_date'

@admin.register(CollateralDocument)
class CollateralDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'collateral', 'document_type', 'title', 
        'is_verified', 'uploaded_at', 'expiry_date'
    ]
    list_filter = ['document_type', 'is_verified', 'uploaded_at']
    search_fields = ['collateral__collateral_id', 'title', 'description']
    readonly_fields = ['file_size', 'mime_type', 'uploaded_at']
