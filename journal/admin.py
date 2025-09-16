from django.contrib import admin
from .models import Journal, JournalLine


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    fields = ('description', 'account_code', 'tax_rate', 'debit', 'credit')
    readonly_fields = ('line_order', 'company')


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'company', 'date', 'status', 'total_amount', 'is_balanced', 'created_by', 'created_at')
    list_filter = ('status', 'company', 'date', 'created_at')
    search_fields = ('narration', 'reference', 'id', 'company__name')
    readonly_fields = ('created_at', 'updated_at', 'is_balanced', 'total_amount')
    inlines = [JournalLineInline]
    
    fieldsets = (
        ('Journal Information', {
            'fields': ('company', 'narration', 'reference', 'date', 'auto_reversing_date')
        }),
        ('Settings', {
            'fields': ('cash_basis', 'amount_mode', 'status')
        }),
        ('Audit Info', {
            'fields': ('created_by', 'created_at', 'updated_at', 'is_balanced', 'total_amount'),
            'classes': ('collapse',)
        })
    )


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ('journal', 'company', 'account_code', 'description', 'debit', 'credit', 'line_order')
    list_filter = ('journal__status', 'company', 'account_code')
    search_fields = ('description', 'account_code', 'journal__narration', 'company__name')
    readonly_fields = ('created_at', 'updated_at')
