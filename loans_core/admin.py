from django.contrib import admin
from .models import LoanProduct, LoanApplication, Loan

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'min_amount', 'max_amount', 'default_interest_rate', 'is_active', 'company']
    list_filter = ['company', 'category', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['company', 'created_by', 'updated_by']
    fieldsets = (
        ('Company & Basic Information', {
            'fields': ('company', 'name', 'code', 'category', 'description')
        }),
        ('Loan Limits', {
            'fields': ('min_amount', 'max_amount', 'min_term_months', 'max_term_months')
        }),
        ('Interest & Fees', {
            'fields': ('default_interest_rate', 'allows_prepayment', 'prepayment_penalty_rate')
        }),
        ('Late Payment Configuration', {
            'fields': ('grace_period_days', 'late_fee_amount', 'late_fee_percentage')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter products by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_id', 'customer', 'loan_product', 'requested_amount', 'status', 'application_date', 'company']
    list_filter = ['company', 'status', 'loan_product', 'repayment_method', 'payment_frequency', 'application_date']
    search_fields = ['application_id', 'customer__first_name', 'customer__last_name', 'customer__email']
    readonly_fields = ['application_id', 'application_date', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'customer', 'assigned_officer', 'created_by', 'updated_by']
    fieldsets = (
        ('Company & Application Details', {
            'fields': ('company', 'application_id', 'customer', 'loan_product', 'status', 'assigned_officer')
        }),
        ('Loan Terms', {
            'fields': ('requested_amount', 'approved_amount', 'term_months', 'interest_rate')
        }),
        ('Repayment Configuration', {
            'fields': ('repayment_method', 'payment_frequency', 'grace_period_months', 'balloon_payment_amount')
        }),
        ('Important Dates', {
            'fields': ('application_date', 'approval_date', 'disbursement_date', 'first_payment_date')
        }),
        ('Documentation', {
            'fields': ('purpose', 'collateral_description', 'notes', 'rejection_reason')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter applications by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_number', 'customer', 'principal_amount', 'current_balance', 'status', 'next_payment_date', 'days_overdue', 'company']
    list_filter = ['company', 'status', 'loan_product', 'disbursement_date']
    search_fields = ['loan_number', 'customer__first_name', 'customer__last_name', 'application__application_id']
    readonly_fields = ['loan_number', 'application', 'disbursement_date', 'maturity_date', 'is_overdue', 'payment_performance_ratio', 'created_at', 'updated_at']
    raw_id_fields = ['company', 'customer', 'created_by', 'updated_by']
    fieldsets = (
        ('Company & Loan Information', {
            'fields': ('company', 'loan_number', 'application', 'customer', 'loan_product', 'status')
        }),
        ('Financial Details', {
            'fields': ('principal_amount', 'current_balance', 'interest_rate', 'term_months', 'monthly_payment')
        }),
        ('Payment Status', {
            'fields': ('payments_made', 'payments_remaining', 'next_payment_date', 'last_payment_date', 'payment_performance_ratio')
        }),
        ('Important Dates', {
            'fields': ('disbursement_date', 'first_payment_date', 'maturity_date')
        }),
        ('Financial Totals', {
            'fields': ('total_interest_charged', 'total_fees_charged', 'total_payments_received')
        }),
        ('Risk Metrics', {
            'fields': ('days_overdue', 'overdue_amount', 'highest_days_overdue', 'is_overdue')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter loans by user's accessible companies"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user_access__user=request.user)
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing loan
            readonly.extend(['principal_amount', 'interest_rate', 'term_months'])
        return readonly
