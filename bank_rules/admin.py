"""
Bank Rules Admin Interface
---------------------------
Django admin for managing bank reconciliation rules.
"""

from django.contrib import admin
from .models import BankRule, BankRuleCondition


class BankRuleConditionInline(admin.TabularInline):
    """Inline editor for rule conditions"""
    model = BankRuleCondition
    extra = 1
    fields = ('field', 'operator', 'value', 'value_secondary', 'case_sensitive', 'order')
    ordering = ('order',)


@admin.register(BankRule)
class BankRuleAdmin(admin.ModelAdmin):
    """Admin interface for bank rules"""
    
    list_display = (
        'name',
        'company',
        'is_active',
        'priority',
        'match_logic',
        'times_matched',
        'last_matched',
        'created_at'
    )
    
    list_filter = (
        'is_active',
        'company',
        'match_logic',
        'created_at'
    )
    
    search_fields = (
        'name',
        'description',
        'company__name'
    )
    
    readonly_fields = (
        'times_matched',
        'last_matched',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'name', 'description')
        }),
        ('Matching Logic', {
            'fields': ('match_logic',)
        }),
        ('Actions (Suggestions)', {
            'fields': ('suggested_who', 'suggested_what', 'suggested_coa'),
            'description': 'What to suggest when this rule matches'
        }),
        ('Settings', {
            'fields': ('is_active', 'priority')
        }),
        ('Statistics', {
            'fields': ('times_matched', 'last_matched', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [BankRuleConditionInline]
    
    def save_model(self, request, obj, form, change):
        """Set created_by on new rules"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BankRuleCondition)
class BankRuleConditionAdmin(admin.ModelAdmin):
    """Admin interface for rule conditions (optional, mainly use inline)"""
    
    list_display = (
        'rule',
        'field',
        'operator',
        'value',
        'order'
    )
    
    list_filter = (
        'field',
        'operator',
        'rule__company'
    )
    
    search_fields = (
        'rule__name',
        'value'
    )
