from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import re
import json
from decimal import Decimal


class BaseFinancialRule(models.Model):
    """
    Base model for all financial rules in the system.
    Rules define how transactions should be automatically split based on conditions.
    """
    
    RULE_TYPES = [
        ('loan_payment', 'Loan Payment Rule'),
        ('contact_based', 'Contact-Based Rule'),
        ('amount_based', 'Amount-Based Rule'),
        ('description_based', 'Description-Based Rule'),
        ('custom', 'Custom Rule'),
    ]
    
    # Basic Information
    name = models.CharField(
        max_length=100, 
        help_text="Descriptive name for this rule (e.g., 'Rodriguez Loan Payment Split')"
    )
    description = models.TextField(
        blank=True, 
        help_text="Optional description explaining what this rule does"
    )
    rule_type = models.CharField(
        max_length=20, 
        choices=RULE_TYPES,
        help_text="Type of rule for categorization and engine selection"
    )
    
    # Relationships
    company = models.ForeignKey(
        'company.Company',
        on_delete=models.CASCADE,
        help_text="Company this rule belongs to"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this rule"
    )
    
    # Rule Behavior
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rule is currently active"
    )
    priority = models.IntegerField(
        default=0,
        help_text="Priority for rule evaluation (higher numbers = higher priority)"
    )
    stop_on_match = models.BooleanField(
        default=True,
        help_text="Stop evaluating other rules after this one matches"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-priority', 'name']
        verbose_name = 'Financial Rule'
        verbose_name_plural = 'Financial Rules'
        indexes = [
            models.Index(fields=['company', 'rule_type', 'is_active']),
            models.Index(fields=['priority', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"
    
    def increment_usage(self):
        """Increment the usage counter and update last used timestamp"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])


class RuleCondition(models.Model):
    """
    Conditions that must be met for a rule to be applied.
    Multiple conditions are evaluated with AND logic.
    """
    
    OPERATORS = [
        ('equals', 'Equals'),
        ('contains', 'Contains'),
        ('starts_with', 'Starts With'),
        ('ends_with', 'Ends With'),
        ('regex', 'Regular Expression'),
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('between', 'Between (range)'),
        ('in_list', 'In List'),
        ('not_equals', 'Not Equals'),
    ]
    
    FIELD_TYPES = [
        ('customer_name', 'Customer Name'),
        ('transaction_amount', 'Transaction Amount'),
        ('transaction_description', 'Transaction Description'),
        ('transaction_date', 'Transaction Date'),
        ('account_code', 'Account Code'),
        ('custom_field', 'Custom Field'),
    ]
    
    rule = models.ForeignKey(
        BaseFinancialRule,
        on_delete=models.CASCADE,
        related_name='conditions'
    )
    
    field_name = models.CharField(
        max_length=50,
        choices=FIELD_TYPES,
        help_text="Field to evaluate"
    )
    operator = models.CharField(
        max_length=20,
        choices=OPERATORS,
        help_text="Comparison operator"
    )
    value = models.TextField(
        help_text="Value to compare against (JSON for complex values)"
    )
    is_case_sensitive = models.BooleanField(
        default=False,
        help_text="Whether string comparisons should be case-sensitive"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Rule Condition'
        verbose_name_plural = 'Rule Conditions'
    
    def __str__(self):
        return f"{self.get_field_name_display()} {self.get_operator_display()} {self.value[:50]}"
    
    def evaluate(self, transaction_data):
        """
        Evaluate this condition against transaction data.
        Returns True if condition is met, False otherwise.
        """
        field_value = transaction_data.get(self.field_name, '')
        target_value = self.value
        
        # Handle case sensitivity for string operations
        if not self.is_case_sensitive and isinstance(field_value, str):
            field_value = field_value.lower()
            target_value = target_value.lower()
        
        # Evaluate based on operator
        if self.operator == 'equals':
            return str(field_value) == str(target_value)
        elif self.operator == 'contains':
            return str(target_value) in str(field_value)
        elif self.operator == 'starts_with':
            return str(field_value).startswith(str(target_value))
        elif self.operator == 'ends_with':
            return str(field_value).endswith(str(target_value))
        elif self.operator == 'regex':
            try:
                pattern = re.compile(target_value)
                return bool(pattern.search(str(field_value)))
            except re.error:
                return False
        elif self.operator in ['gt', 'gte', 'lt', 'lte']:
            try:
                field_num = float(field_value)
                target_num = float(target_value)
                if self.operator == 'gt':
                    return field_num > target_num
                elif self.operator == 'gte':
                    return field_num >= target_num
                elif self.operator == 'lt':
                    return field_num < target_num
                elif self.operator == 'lte':
                    return field_num <= target_num
            except (ValueError, TypeError):
                return False
        elif self.operator == 'between':
            try:
                # Expected format: "min,max"
                min_val, max_val = target_value.split(',')
                field_num = float(field_value)
                return float(min_val) <= field_num <= float(max_val)
            except (ValueError, TypeError):
                return False
        elif self.operator == 'in_list':
            try:
                # Parse JSON list or comma-separated values
                if target_value.startswith('['):
                    value_list = json.loads(target_value)
                else:
                    value_list = [v.strip() for v in target_value.split(',')]
                return str(field_value) in value_list
            except (json.JSONDecodeError, ValueError):
                return False
        elif self.operator == 'not_equals':
            return str(field_value) != str(target_value)
        
        return False


class RuleAction(models.Model):
    """
    Actions to be executed when a rule matches.
    These define how the transaction should be split.
    """
    
    ALLOCATION_TYPES = [
        ('percentage', 'Percentage of Total'),
        ('fixed_amount', 'Fixed Amount'),
        ('remainder', 'Remainder (auto-calculated)'),
        ('formula', 'Formula-based'),
    ]
    
    rule = models.ForeignKey(
        BaseFinancialRule,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    
    # Sequence for ordering multiple actions
    sequence = models.PositiveIntegerField(
        default=1,
        help_text="Order in which this action should be executed"
    )
    
    # Split Line Details
    description_template = models.CharField(
        max_length=200,
        help_text="Template for the split line description (can use {variables})"
    )
    account_code = models.CharField(
        max_length=10,
        help_text="GL account code for this split line"
    )
    
    # Amount Calculation
    allocation_type = models.CharField(
        max_length=20,
        choices=ALLOCATION_TYPES,
        default='percentage'
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Value for allocation (percentage, fixed amount, etc.)"
    )
    
    # Additional Properties
    tax_treatment = models.CharField(
        max_length=20,
        default='no_gst',
        choices=[
            ('no_gst', 'Tax Exempt'),
            ('gst_free', 'GST Free'),
            ('input_taxed', 'Input Taxed'),
        ]
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sequence', 'id']
        verbose_name = 'Rule Action'
        verbose_name_plural = 'Rule Actions'
    
    def __str__(self):
        return f"{self.description_template} → {self.account_code} ({self.get_allocation_type_display()})"
    
    def calculate_amount(self, transaction_amount, context=None):
        """
        Calculate the split amount based on allocation type and value.
        """
        transaction_amount = Decimal(str(transaction_amount))
        
        if self.allocation_type == 'percentage':
            return (transaction_amount * self.value) / Decimal('100')
        elif self.allocation_type == 'fixed_amount':
            return self.value
        elif self.allocation_type == 'remainder':
            # This will be calculated by the engine after other allocations
            return Decimal('0')
        elif self.allocation_type == 'formula':
            # Future: implement formula evaluation
            return Decimal('0')
        
        return Decimal('0')
    
    def render_description(self, context=None):
        """
        Render the description template with context variables.
        """
        if not context:
            return self.description_template
        
        try:
            return self.description_template.format(**context)
        except (KeyError, ValueError):
            return self.description_template


class RuleExecutionLog(models.Model):
    """
    Log of rule executions for auditing and debugging.
    """
    
    rule = models.ForeignKey(
        BaseFinancialRule,
        on_delete=models.CASCADE,
        related_name='execution_logs'
    )
    
    # Transaction Context
    transaction_data = models.JSONField(
        help_text="Snapshot of transaction data when rule was executed"
    )
    
    # Execution Results
    matched = models.BooleanField(
        help_text="Whether the rule conditions were met"
    )
    actions_executed = models.PositiveIntegerField(
        default=0,
        help_text="Number of actions that were executed"
    )
    result_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Generated split data or error information"
    )
    
    # Metadata
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-executed_at']
        verbose_name = 'Rule Execution Log'
        verbose_name_plural = 'Rule Execution Logs'
        indexes = [
            models.Index(fields=['rule', 'executed_at']),
            models.Index(fields=['matched', 'executed_at']),
        ]
    
    def __str__(self):
        status = "✅ Matched" if self.matched else "❌ No Match"
        return f"{self.rule.name} - {status} at {self.executed_at}"
