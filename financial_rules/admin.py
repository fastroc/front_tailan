from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import BaseFinancialRule, RuleCondition, RuleAction, RuleExecutionLog
from .engines.base_engine import RuleEngineFactory
import json


class RuleConditionInline(admin.TabularInline):
    """
    Inline admin for rule conditions.
    """
    model = RuleCondition
    extra = 1
    fields = ('field_name', 'operator', 'value', 'is_case_sensitive')
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 40})},
    }


class RuleActionInline(admin.TabularInline):
    """
    Inline admin for rule actions.
    """
    model = RuleAction
    extra = 1
    fields = ('sequence', 'description_template', 'account_code', 'allocation_type', 'value', 'tax_treatment')
    ordering = ('sequence',)
    
    formfield_overrides = {
        models.CharField: {'widget': Textarea(attrs={'rows': 1, 'cols': 50})},
    }


@admin.register(BaseFinancialRule)
class BaseFinancialRuleAdmin(admin.ModelAdmin):
    """
    Admin interface for financial rules with enhanced functionality.
    """
    
    list_display = ('name', 'rule_type', 'company', 'is_active', 'priority', 'usage_count', 'last_used_at', 'rule_actions')
    list_filter = ('rule_type', 'is_active', 'company', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-priority', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'rule_type', 'company')
        }),
        ('Rule Behavior', {
            'fields': ('is_active', 'priority', 'stop_on_match'),
            'description': 'Control how this rule behaves when evaluated'
        }),
        ('Statistics', {
            'fields': ('usage_count', 'last_used_at'),
            'classes': ('collapse',),
            'description': 'Usage statistics (read-only)'
        }),
    )
    
    readonly_fields = ('usage_count', 'last_used_at', 'created_at', 'updated_at')
    
    inlines = [RuleConditionInline, RuleActionInline]
    
    actions = ['test_rule', 'duplicate_rule', 'activate_rules', 'deactivate_rules']
    
    def rule_actions(self, obj):
        """Display number of actions for this rule"""
        count = obj.actions.count()
        if count > 0:
            return format_html(
                '<span style="color: green;">{} action{}</span>',
                count,
                's' if count != 1 else ''
            )
        return format_html('<span style="color: orange;">No actions</span>')
    rule_actions.short_description = 'Actions'
    
    def get_urls(self):
        """Add custom URLs for rule testing"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:rule_id>/test/',
                self.admin_site.admin_view(self.test_rule_view),
                name='financial_rules_basefinancialrule_test'
            ),
        ]
        return custom_urls + urls
    
    def test_rule_view(self, request, rule_id):
        """Custom view for testing rules"""
        rule = get_object_or_404(BaseFinancialRule, id=rule_id)
        
        if request.method == 'POST':
            try:
                test_data = json.loads(request.POST.get('test_data', '{}'))
                
                # Create engine and test rule
                engine = RuleEngineFactory.create_engine(rule.company_id)
                result = engine.test_rule(rule_id, test_data)
                
                return JsonResponse({
                    'success': result.success,
                    'error_message': result.error_message,
                    'split_data': result.split_data,
                    'total_allocated': str(result.total_allocated)
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error_message': f'Test error: {str(e)}'
                })
        
        # Default test data
        test_data = {
            'customer_name': 'Test Customer',
            'transaction_amount': 100.00,
            'transaction_description': 'Test transaction',
        }
        
        context = {
            'rule': rule,
            'test_data_json': json.dumps(test_data, indent=2),
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        
        return render(request, 'admin/financial_rules/test_rule.html', context)
    
    def test_rule(self, request, queryset):
        """Action to test selected rules"""
        if queryset.count() != 1:
            messages.error(request, 'Please select exactly one rule to test.')
            return
        
        rule = queryset.first()
        test_url = reverse('admin:financial_rules_basefinancialrule_test', args=[rule.id])
        messages.info(
            request, 
            format_html(
                'Use the <a href="{}" target="_blank">rule testing interface</a> to test this rule.',
                test_url
            )
        )
    test_rule.short_description = 'Test selected rule'
    
    def duplicate_rule(self, request, queryset):
        """Action to duplicate rules"""
        for rule in queryset:
            # Create a copy of the rule
            new_rule = BaseFinancialRule.objects.create(
                name=f"{rule.name} (Copy)",
                description=rule.description,
                rule_type=rule.rule_type,
                company=rule.company,
                is_active=False,  # Start as inactive
                priority=rule.priority,
                stop_on_match=rule.stop_on_match,
                created_by=request.user
            )
            
            # Copy conditions
            for condition in rule.conditions.all():
                RuleCondition.objects.create(
                    rule=new_rule,
                    field_name=condition.field_name,
                    operator=condition.operator,
                    value=condition.value,
                    is_case_sensitive=condition.is_case_sensitive
                )
            
            # Copy actions
            for action in rule.actions.all():
                RuleAction.objects.create(
                    rule=new_rule,
                    sequence=action.sequence,
                    description_template=action.description_template,
                    account_code=action.account_code,
                    allocation_type=action.allocation_type,
                    value=action.value,
                    tax_treatment=action.tax_treatment
                )
        
        messages.success(request, f'Successfully duplicated {queryset.count()} rule(s).')
    duplicate_rule.short_description = 'Duplicate selected rules'
    
    def activate_rules(self, request, queryset):
        """Action to activate rules"""
        updated = queryset.update(is_active=True)
        messages.success(request, f'Activated {updated} rule(s).')
    activate_rules.short_description = 'Activate selected rules'
    
    def deactivate_rules(self, request, queryset):
        """Action to deactivate rules"""
        updated = queryset.update(is_active=False)
        messages.success(request, f'Deactivated {updated} rule(s).')
    deactivate_rules.short_description = 'Deactivate selected rules'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new rules"""
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RuleCondition)
class RuleConditionAdmin(admin.ModelAdmin):
    """
    Admin interface for rule conditions.
    """
    
    list_display = ('rule', 'field_name', 'operator', 'value_preview', 'is_case_sensitive')
    list_filter = ('field_name', 'operator', 'is_case_sensitive')
    search_fields = ('rule__name', 'value')
    
    def value_preview(self, obj):
        """Show preview of condition value"""
        if len(obj.value) > 50:
            return obj.value[:47] + '...'
        return obj.value
    value_preview.short_description = 'Value'


@admin.register(RuleAction)
class RuleActionAdmin(admin.ModelAdmin):
    """
    Admin interface for rule actions.
    """
    
    list_display = ('rule', 'sequence', 'description_template', 'account_code', 'allocation_type', 'value')
    list_filter = ('allocation_type', 'tax_treatment')
    search_fields = ('rule__name', 'description_template', 'account_code')
    ordering = ('rule', 'sequence')


@admin.register(RuleExecutionLog)
class RuleExecutionLogAdmin(admin.ModelAdmin):
    """
    Admin interface for rule execution logs.
    """
    
    list_display = ('rule', 'matched', 'actions_executed', 'executed_at', 'executed_by')
    list_filter = ('matched', 'executed_at', 'rule__rule_type')
    search_fields = ('rule__name',)
    readonly_fields = ('rule', 'transaction_data', 'matched', 'actions_executed', 'result_data', 'executed_at', 'executed_by')
    
    def has_add_permission(self, request):
        """Disable adding logs manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make logs read-only"""
        return False


# Customize admin site header
admin.site.site_header = 'Financial Rules Administration'
admin.site.site_title = 'Financial Rules Admin'
admin.site.index_title = 'Financial Rules Management'
