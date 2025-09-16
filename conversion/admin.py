from django.contrib import admin
from django.utils.html import format_html
from .models import ConversionDate, ConversionBalance, ConversionPeriod


@admin.register(ConversionDate)
class ConversionDateAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'conversion_date', 'as_at_date_display', 
        'balances_count', 'created_at'
    ]
    list_filter = ['conversion_date', 'created_at']
    search_fields = ['company__name']
    readonly_fields = ['as_at_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Conversion Information', {
            'fields': ('company', 'conversion_date')
        }),
        ('Calculated Fields', {
            'fields': ('as_at_date',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def as_at_date_display(self, obj):
        """Display the as-at date with formatting"""
        if obj.conversion_date:
            as_at = obj.as_at_date
            return format_html(
                '<span class="badge bg-info">{}</span>',
                as_at.strftime('%d %b %Y')
            )
        return '-'
    as_at_date_display.short_description = 'As At Date'
    
    def balances_count(self, obj):
        """Count of conversion balances"""
        count = obj.company.conversion_balances.count()
        if count > 0:
            return format_html(
                '<span class="badge bg-success">{} balances</span>',
                count
            )
        return format_html('<span class="badge bg-warning">No balances</span>')
    balances_count.short_description = 'Balances'


@admin.register(ConversionBalance)
class ConversionBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'account_display', 'company', 'as_at_date', 
        'debit_display', 'credit_display', 'balance_type_display', 'updated_at'
    ]
    list_filter = [
        'company', 'as_at_date', 'account__account_type', 
        'created_at', 'updated_at'
    ]
    search_fields = [
        'account__code', 'account__name', 'company__name', 'notes'
    ]
    readonly_fields = ['net_amount', 'balance_type', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Balance Information', {
            'fields': ('company', 'account', 'as_at_date')
        }),
        ('Amounts', {
            'fields': ('debit_amount', 'credit_amount'),
            'description': 'Enter either debit OR credit amount, not both.'
        }),
        ('Calculated Fields', {
            'fields': ('net_amount', 'balance_type'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def account_display(self, obj):
        """Display account with code and name"""
        return format_html(
            '<strong>{}</strong><br><small class="text-muted">{}</small>',
            obj.account.code,
            obj.account.name
        )
    account_display.short_description = 'Account'
    
    def debit_display(self, obj):
        """Display debit amount with formatting"""
        if obj.debit_amount > 0:
            return format_html(
                '<span class="badge bg-primary">${}</span>',
                f'{obj.debit_amount:,.2f}'
            )
        return '-'
    debit_display.short_description = 'Debit'
    
    def credit_display(self, obj):
        """Display credit amount with formatting"""
        if obj.credit_amount > 0:
            return format_html(
                '<span class="badge bg-success">${}</span>',
                f'{obj.credit_amount:,.2f}'
            )
        return '-'
    credit_display.short_description = 'Credit'
    
    def balance_type_display(self, obj):
        """Display balance type with color coding"""
        balance_type = obj.balance_type
        if balance_type == 'Debit':
            color = 'primary'
        elif balance_type == 'Credit':
            color = 'success'
        else:
            color = 'secondary'
        
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            balance_type
        )
    balance_type_display.short_description = 'Type'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'company', 'account'
        )


@admin.register(ConversionPeriod)
class ConversionPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'name', 'period_type', 'date_range_display', 
        'is_active'
    ]
    list_filter = ['period_type', 'is_active', 'start_date']
    search_fields = ['company__name', 'name']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('company', 'name', 'period_type')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date', 'is_active')
        })
    )
    
    def date_range_display(self, obj):
        """Display date range with formatting"""
        return format_html(
            '<span class="badge bg-info">{} - {}</span>',
            obj.start_date.strftime('%d %b %Y'),
            obj.end_date.strftime('%d %b %Y')
        )
    date_range_display.short_description = 'Date Range'


# Add conversion balance summary to Company admin - temporarily disabled
# TODO: Fix the method binding issue with CompanyAdmin

# def conversion_summary_display(self, obj):
#     """Display conversion balance summary"""
#     try:
#         conv_date = getattr(obj, 'conversion_date', None)
#         balances_count = obj.conversion_balances.count()
#         
#         if conv_date and balances_count > 0:
#             # Calculate total debits and credits
#             totals = obj.conversion_balances.aggregate(
#                 total_debits=Sum('debit_amount'),
#                 total_credits=Sum('credit_amount')
#             )
#             
#             total_dr = totals['total_debits'] or 0
#             total_cr = totals['total_credits'] or 0
#             difference = total_dr - total_cr
#             
#             status = "✅ Balanced" if difference == 0 else f"⚠️ Diff: ${difference:,.2f}"
#             
#             return format_html(
#                 '''
#                 <div class="small">
#                     <div><strong>Conversion Date:</strong> {}</div>
#                     <div><strong>Balances:</strong> {} entries</div>
#                     <div><strong>Total DR:</strong> ${:,.2f}</div>
#                     <div><strong>Total CR:</strong> ${:,.2f}</div>
#                     <div><strong>Status:</strong> {}</div>
#                 </div>
#                 ''',
#                 conv_date.conversion_date.strftime('%d %b %Y'),
#                 balances_count,
#                 total_dr,
#                 total_cr,
#                 status
#             )
#         elif conv_date:
#             return mark_safe(
#                 f'<span class="badge bg-warning">Conversion date set: '
#                 f'{conv_date.conversion_date.strftime("%d %b %Y")}<br>No balances entered</span>'
#             )
#         else:
#             return mark_safe('<span class="badge bg-secondary">Not configured</span>')
#     except Exception:
#         return mark_safe('<span class="badge bg-secondary">Not configured</span>')

# conversion_summary_display.short_description = '🔄 Conversion Status'

# # Properly add the method to CompanyAdmin class
# setattr(CompanyAdmin, 'conversion_summary_display', conversion_summary_display)

# # Add the conversion summary to Company admin list display if not already present
# if hasattr(CompanyAdmin, 'list_display'):
#     current_display = list(CompanyAdmin.list_display)
#     if 'conversion_summary_display' not in current_display:
#         CompanyAdmin.list_display = current_display + ['conversion_summary_display']
