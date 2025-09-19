from django.contrib import admin
from .models import Customer, CustomerDocument

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'full_name', 'email', 'customer_type', 'monthly_income', 'risk_rating', 'is_active']
    list_filter = ['customer_type', 'employment_type', 'marital_status', 'risk_rating', 'is_active', 'created_at']
    search_fields = ['customer_id', 'first_name', 'last_name', 'email', 'national_id', 'business_name']
    readonly_fields = ['customer_id', 'created_at', 'updated_at', 'total_monthly_income', 'debt_to_income_ratio']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_id', 'customer_type', 'is_active', 'risk_rating')
        }),
        ('Personal Details', {
            'fields': ('first_name', 'last_name', 'middle_name', 'date_of_birth', 'national_id', 'marital_status', 'dependents_count'),
            'classes': ('collapse',)
        }),
        ('Business Details', {
            'fields': ('business_name', 'business_registration_number', 'business_type', 'years_in_business', 'annual_revenue'),
            'classes': ('collapse',)
        }),
        ('Contact Information', {
            'fields': ('email', 'phone_primary', 'phone_secondary')
        }),
        ('Address', {
            'fields': ('street_address', 'city', 'state_province', 'postal_code', 'country'),
            'classes': ('collapse',)
        }),
        ('Employment & Income', {
            'fields': ('employment_type', 'employer_name', 'job_title', 'employment_duration_months', 'monthly_income', 'other_income', 'total_monthly_income')
        }),
        ('Financial Information', {
            'fields': ('monthly_expenses', 'existing_debt_payments', 'debt_to_income_ratio', 'credit_score')
        }),
        ('Banking Information', {
            'fields': ('bank_name', 'account_number', 'routing_number', 'account_type'),
            'classes': ('collapse',)
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = list(self.fieldsets)
        if obj and obj.customer_type == 'individual':
            # Hide business fields for individual customers
            fieldsets = [fs for fs in fieldsets if fs[0] != 'Business Details']
        elif obj and obj.customer_type == 'business':
            # Modify personal details for business customers
            personal_fields = list(fieldsets[1][1]['fields'])
            personal_fields = [f for f in personal_fields if f not in ['marital_status', 'dependents_count']]
            fieldsets[1] = ('Contact Person Details', {'fields': tuple(personal_fields), 'classes': ('collapse',)})
        return fieldsets

@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'document_type', 'document_name', 'status', 'created_at', 'expiry_date', 'is_expired']
    list_filter = ['document_type', 'status', 'created_at', 'expiry_date']
    search_fields = ['customer__first_name', 'customer__last_name', 'document_name', 'document_number']
    readonly_fields = ['created_at', 'file_size_mb', 'is_expired']
    raw_id_fields = ['customer', 'reviewed_by', 'created_by']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('customer', 'document_type', 'document_name', 'file_path', 'file_size_mb')
        }),
        ('Document Details', {
            'fields': ('description', 'issue_date', 'expiry_date', 'document_number', 'is_expired')
        }),
        ('Review Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New document
            obj.created_by = request.user
        if obj.status in ['approved', 'rejected'] and not obj.reviewed_by:
            obj.reviewed_by = request.user
            from django.utils import timezone
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
