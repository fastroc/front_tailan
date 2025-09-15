from django.contrib import admin
from django.utils.html import format_html
from .models import ReconciliationSession, TransactionMatch, TransactionSplit, ReconciliationReport


class TransactionSplitInline(admin.TabularInline):
    """Inline admin for transaction splits"""
    model = TransactionSplit
    extra = 0
    readonly_fields = ('tax_amount', 'net_amount', 'created_at')
    fields = ('split_number', 'amount', 'gl_account', 'description', 'tax_rate', 'tax_amount', 'net_amount')


@admin.register(TransactionMatch)
class TransactionMatchAdmin(admin.ModelAdmin):
    """Enhanced admin for TransactionMatch with split support"""
    list_display = ('id', 'transaction_description', 'transaction_amount', 'match_type_display', 'gl_account_display', 'is_reconciled', 'matched_at')
    list_filter = ('match_type', 'is_reconciled', 'matched_at', 'reconciliation_session__account')
    search_fields = ('bank_transaction__description', 'contact', 'description', 'gl_account__name')
    readonly_fields = ('match_confidence', 'matched_at', 'journal_entry')
    inlines = [TransactionSplitInline]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('bank_transaction', 'reconciliation_session', 'match_type', 'match_confidence')
        }),
        ('WHO/WHAT/WHY/TAX', {
            'fields': ('contact', 'gl_account', 'description', 'tax_rate')
        }),
        ('Status & Integration', {
            'fields': ('is_reconciled', 'journal_entry', 'matched_by', 'matched_at')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    def transaction_description(self, obj):
        return obj.bank_transaction.description[:50] + "..." if len(obj.bank_transaction.description) > 50 else obj.bank_transaction.description
    transaction_description.short_description = 'Transaction'
    
    def transaction_amount(self, obj):
        amount = obj.bank_transaction.amount
        color = 'green' if amount > 0 else 'red'
        amount_formatted = '{:.2f}'.format(float(amount))
        return format_html('<span style="color: {};">${}</span>', color, amount_formatted)
    transaction_amount.short_description = 'Amount'
    
    def match_type_display(self, obj):
        if obj.is_split_transaction:
            split_count = obj.splits.count()
            return format_html(
                '<span style="color: blue; font-weight: bold;">🔀 Split ({} lines)</span> '
                '<a href="/admin/reconciliation/transactionsplit/?transaction_match__id={}" '
                'style="font-size: 11px; color: #666;">[View Splits]</a>', 
                split_count, obj.id
            )
        return obj.match_type.title()
    match_type_display.short_description = 'Type'
    
    def gl_account_display(self, obj):
        if obj.gl_account:
            return obj.gl_account.name
        elif obj.is_split_transaction:
            splits = obj.splits.all()[:3]  # Show first 3 splits
            split_names = [split.gl_account.name for split in splits]
            display = ', '.join(split_names)
            if obj.splits.count() > 3:
                more_count = obj.splits.count() - 3
                display += ' (+{} more)'.format(more_count)
            return format_html('<small>{}</small>', display)
        return format_html('<em style="color: #999;">No GL Account</em>')
    gl_account_display.short_description = 'GL Account(s)'


@admin.register(TransactionSplit)
class TransactionSplitAdmin(admin.ModelAdmin):
    """Admin for individual transaction splits"""
    list_display = ('id', 'main_transaction_id', 'transaction_match_summary', 'split_number', 'amount', 'gl_account', 'tax_amount', 'created_at')
    list_filter = ('transaction_match__id', 'gl_account__account_type', 'created_at', 'transaction_match__reconciliation_session__account')
    search_fields = ('description', 'gl_account__name', 'transaction_match__bank_transaction__description', 'transaction_match__id')
    readonly_fields = ('tax_amount', 'net_amount', 'created_at')
    
    fieldsets = (
        ('Split Details', {
            'fields': ('transaction_match', 'split_number', 'amount')
        }),
        ('WHO/WHAT/WHY/TAX', {
            'fields': ('contact', 'gl_account', 'description', 'tax_rate')
        }),
        ('Calculated Values', {
            'fields': ('tax_amount', 'net_amount'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def main_transaction_id(self, obj):
        """Display the main transaction match ID prominently"""
        match_id = obj.transaction_match.id
        return format_html('<a href="/admin/reconciliation/transactionmatch/{}/change/" style="font-weight: bold; color: #0066cc;">Match #{}</a>', match_id, match_id)
    main_transaction_id.short_description = 'Main Transaction'
    main_transaction_id.admin_order_field = 'transaction_match__id'
    
    def transaction_match_summary(self, obj):
        return "Match #{}: {}...".format(obj.transaction_match.id, obj.transaction_match.bank_transaction.description[:30])
    transaction_match_summary.short_description = 'Transaction Match'


@admin.register(ReconciliationSession)
class ReconciliationSessionAdmin(admin.ModelAdmin):
    """Admin for reconciliation sessions"""
    list_display = ('id', 'session_name', 'account', 'status', 'reconciliation_percentage', 'period_end', 'created_at')
    list_filter = ('status', 'account', 'created_at')
    search_fields = ('session_name', 'account__name')
    readonly_fields = ('total_transactions', 'matched_transactions', 'unmatched_transactions', 'reconciliation_percentage', 'created_at')
    
    fieldsets = (
        ('Session Info', {
            'fields': ('account', 'session_name', 'period_start', 'period_end')
        }),
        ('Balances', {
            'fields': ('opening_balance', 'closing_balance', 'statement_balance')
        }),
        ('Progress', {
            'fields': ('status', 'total_transactions', 'matched_transactions', 'unmatched_transactions'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ReconciliationReport)
class ReconciliationReportAdmin(admin.ModelAdmin):
    """Admin for reconciliation reports"""
    list_display = ('id', 'reconciliation_session', 'reconciliation_percentage', 'total_reconciled', 'generated_at')
    list_filter = ('generated_at', 'reconciliation_session__account')
    readonly_fields = ('reconciliation_percentage', 'generated_at', 'report_data')
    
    def reconciliation_percentage(self, obj):
        percentage = obj.reconciliation_percentage()
        color = 'green' if percentage == 100 else 'orange' if percentage >= 80 else 'red'
        percentage_formatted = '{:.1f}'.format(float(percentage))
        return format_html('<span style="color: {}; font-weight: bold;">{}%</span>', color, percentage_formatted)
    reconciliation_percentage.short_description = 'Progress'
