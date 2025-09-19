from django.contrib import admin
from .models import Payment, PaymentAllocation, PaymentHistory, AutoPayment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'loan', 'payment_amount', 'payment_method', 'status', 'payment_date', 'company']
    list_filter = ['company', 'status', 'payment_method', 'payment_date', 'payment_type']
    search_fields = ['payment_id', 'transaction_id', 'loan__loan_number', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['payment_id', 'net_payment_amount', 'effective_payment_amount', 'is_successful', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'loan', 'customer', 'scheduled_payment', 'processed_by', 'created_by', 'updated_by']
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Company & Payment Information', {
            'fields': ('company', 'payment_id', 'transaction_id', 'loan', 'customer', 'scheduled_payment')
        }),
        ('Payment Details', {
            'fields': ('payment_date', 'payment_amount', 'net_payment_amount', 'payment_method', 'payment_type')
        }),
        ('Status & Processing', {
            'fields': ('status', 'processed_date', 'processed_by', 'is_successful')
        }),
        ('Payment Source', {
            'fields': ('bank_name', 'account_last_four'),
            'classes': ('collapse',)
        }),
        ('Fees and Charges', {
            'fields': ('processing_fee', 'late_fee_included', 'effective_payment_amount')
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter payments by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f"{queryset.count()} payments marked as completed.")
    mark_as_completed.short_description = "Mark selected payments as completed"
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
        self.message_user(request, f"{queryset.count()} payments marked as failed.")
    mark_as_failed.short_description = "Mark selected payments as failed"

class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    readonly_fields = ['balance_before', 'balance_after', 'created_at']
    fields = ['scheduled_payment', 'allocation_type', 'allocation_amount', 'allocation_order', 'description', 'balance_before', 'balance_after']

@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ['payment', 'scheduled_payment', 'allocation_amount', 'allocation_type', 'company']
    list_filter = ['company', 'allocation_type', 'created_at']
    search_fields = ['payment__payment_id', 'loan__loan_number', 'description']
    readonly_fields = ['balance_before', 'balance_after', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'payment', 'loan', 'scheduled_payment', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Company & Allocation Information', {
            'fields': ('company', 'payment', 'loan', 'scheduled_payment', 'allocation_type', 'allocation_order')
        }),
        ('Allocation Details', {
            'fields': ('allocation_amount', 'description', 'notes')
        }),
        ('Balance Impact', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter allocations by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['payment', 'action_type', 'action_date', 'performed_by', 'old_status', 'new_status', 'company']
    list_filter = ['company', 'action_type', 'action_date', 'old_status', 'new_status']
    search_fields = ['payment__payment_id', 'description', 'performed_by__username']
    readonly_fields = ['action_date', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'payment', 'performed_by', 'created_by', 'updated_by']
    date_hierarchy = 'action_date'
    
    fieldsets = (
        ('Company & History Information', {
            'fields': ('company', 'payment', 'action_type', 'action_date', 'performed_by')
        }),
        ('Change Details', {
            'fields': ('old_status', 'new_status', 'old_amount', 'new_amount')
        }),
        ('Additional Context', {
            'fields': ('description', 'system_notes')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter payment history by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(AutoPayment)
class AutoPaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'payment_amount', 'frequency', 'next_payment_date', 'is_active', 'status', 'company']
    list_filter = ['company', 'frequency', 'is_active', 'status', 'account_type']
    search_fields = ['loan__loan_number', 'customer__first_name', 'customer__last_name', 'bank_account_name']
    readonly_fields = ['current_failures', 'last_failure_date', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'loan', 'customer', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Company & AutoPay Information', {
            'fields': ('company', 'loan', 'customer', 'is_active', 'status', 'frequency')
        }),
        ('Payment Configuration', {
            'fields': ('payment_amount', 'payment_day', 'next_payment_date', 'next_payment_amount')
        }),
        ('Banking Information', {
            'fields': ('bank_account_name', 'bank_routing_number', 'bank_account_number_encrypted', 'account_type')
        }),
        ('Failure Handling', {
            'fields': ('max_retry_attempts', 'current_failures', 'last_failure_date', 'last_failure_reason'),
            'classes': ('collapse',)
        }),
        ('Agreement Details', {
            'fields': ('agreement_date', 'agreement_ip_address', 'terms_accepted'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter auto payments by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)
    
    actions = ['activate_autopay', 'pause_autopay', 'reset_failure_count']
    
    def activate_autopay(self, request, queryset):
        queryset.update(is_active=True, status='active')
        self.message_user(request, f"{queryset.count()} autopay configurations activated.")
    activate_autopay.short_description = "Activate selected autopay configurations"
    
    def pause_autopay(self, request, queryset):
        queryset.update(status='paused')
        self.message_user(request, f"{queryset.count()} autopay configurations paused.")
    pause_autopay.short_description = "Pause selected autopay configurations"
    
    def reset_failure_count(self, request, queryset):
        for autopay in queryset:
            autopay.current_failures = 0
            autopay.save()
        self.message_user(request, f"Reset failure count for {queryset.count()} autopay configurations.")
    reset_failure_count.short_description = "Reset failure count for selected configurations"

# Add inline to Payment admin
PaymentAdmin.inlines = [PaymentAllocationInline]
