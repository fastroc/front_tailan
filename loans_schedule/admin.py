from django.contrib import admin
from .models import PaymentSchedule, ScheduledPayment, CustomPaymentPreset, PaymentDateRule

@admin.register(PaymentSchedule)
class PaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ['loan', 'schedule_type', 'payment_frequency', 'total_payments', 'payments_completed', 'completion_percentage', 'status', 'company']
    list_filter = ['company', 'schedule_type', 'payment_frequency', 'status', 'created_at']
    search_fields = ['loan__loan_number', 'loan__customer__first_name', 'loan__customer__last_name']
    readonly_fields = ['completion_percentage', 'remaining_payments', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'loan', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Company & Schedule Information', {
            'fields': ('company', 'loan', 'schedule_type', 'payment_frequency', 'status')
        }),
        ('Payment Counts', {
            'fields': ('total_payments', 'payments_completed', 'completion_percentage', 'remaining_payments')
        }),
        ('Financial Totals', {
            'fields': ('total_principal', 'total_interest', 'total_amount')
        }),
        ('Special Features', {
            'fields': ('grace_period_months', 'balloon_payment_amount')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter schedules by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(ScheduledPayment)
class ScheduledPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_schedule', 'payment_number', 'due_date', 'total_amount', 'amount_paid', 'status', 'days_overdue', 'company']
    list_filter = ['company', 'status', 'payment_type', 'due_date', 'is_custom_amount']
    search_fields = ['payment_schedule__loan__loan_number', 'payment_schedule__loan__customer__first_name', 'payment_schedule__loan__customer__last_name']
    readonly_fields = ['is_overdue', 'remaining_amount', 'is_fully_paid', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'payment_schedule', 'loan', 'created_by', 'updated_by']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Company & Payment Information', {
            'fields': ('company', 'payment_schedule', 'loan', 'payment_number', 'payment_type', 'due_date')
        }),
        ('Payment Breakdown', {
            'fields': ('principal_amount', 'interest_amount', 'total_amount', 'beginning_balance', 'ending_balance')
        }),
        ('Payment Status', {
            'fields': ('status', 'amount_paid', 'remaining_amount', 'payment_date', 'is_fully_paid')
        }),
        ('Late Payment Tracking', {
            'fields': ('days_overdue', 'is_overdue', 'late_fees_assessed')
        }),
        ('Custom Payment Features', {
            'fields': ('is_custom_amount', 'original_amount'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter scheduled payments by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(CustomPaymentPreset)
class CustomPaymentPresetAdmin(admin.ModelAdmin):
    list_display = ['name', 'preset_type', 'default_frequency', 'usage_count', 'has_balloon_payment', 'is_active', 'company']
    list_filter = ['company', 'preset_type', 'default_frequency', 'has_balloon_payment', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Company & Preset Information', {
            'fields': ('company', 'name', 'description', 'preset_type', 'is_active')
        }),
        ('Default Configuration', {
            'fields': ('default_frequency', 'grace_period_months')
        }),
        ('Custom Schedule Configuration', {
            'fields': ('payment_pattern',),
            'classes': ('collapse',)
        }),
        ('Special Features', {
            'fields': ('has_balloon_payment', 'balloon_percentage')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter presets by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(PaymentDateRule)
class PaymentDateRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_name', 'rule_type', 'day_of_month', 'weekday', 'skip_weekends', 'skip_holidays', 'is_active', 'company']
    list_filter = ['company', 'rule_type', 'skip_weekends', 'skip_holidays', 'is_active', 'created_at']
    search_fields = ['rule_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['company', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Company & Rule Information', {
            'fields': ('company', 'rule_name', 'rule_type', 'is_active')
        }),
        ('Rule Parameters', {
            'fields': ('day_of_month', 'weekday', 'custom_dates')
        }),
        ('Business Rules', {
            'fields': ('skip_weekends', 'skip_holidays')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter payment date rules by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)
