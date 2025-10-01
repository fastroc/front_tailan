"""
Bank Rules Models
-----------------
Flexible rule-based transaction matching for automated reconciliation.

Design Principle: Modular & Safe
- Can be disabled without affecting core reconciliation
- Rules suggest actions (user must click Apply)
- Per-company isolation
- Comprehensive field matching (description, amount, debit/credit, etc.)
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from company.models import Company
from coa.models import Account


class BankRule(models.Model):
    """
    Bank reconciliation rule - matches transactions and suggests actions.
    
    Example Use Cases:
    - "Description contains 'RENT' → Suggest Landlord + Rent Expense"
    - "Amount equals -500000 AND Debit → Suggest specific COA"
    - "Description starts with 'SAL' → Suggest Salary account"
    """
    
    # Ownership
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE,
        related_name='bank_rules',
        help_text="Company that owns this rule"
    )
    
    # Rule Identity
    name = models.CharField(
        max_length=200,
        help_text="E.g., 'Monthly Rent Payment', 'Salary Deposits'"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional: Explain when this rule applies and what it does"
    )
    
    # Matching Logic
    match_logic = models.CharField(
        max_length=10,
        choices=[
            ('ALL', 'All Conditions Must Match (AND)'),
            ('ANY', 'Any Condition Can Match (OR)')
        ],
        default='ALL',
        help_text="How to combine multiple conditions"
    )
    
    # Actions (What to suggest when rule matches)
    suggested_who_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Auto-suggest this correspondent name (WHO field) - can be any text"
    )
    
    suggested_coa = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_rules_suggesting',
        help_text="Auto-suggest this Chart of Account (WHAT field)"
    )
    
    # Settings
    is_active = models.BooleanField(
        default=True,
        help_text="Disable rule without deleting it"
    )
    
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority rules are checked first (0-100, default: 0)"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_bank_rules'
    )
    
    # Statistics
    times_matched = models.IntegerField(
        default=0,
        help_text="How many times this rule has matched transactions"
    )
    
    last_matched = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this rule matched a transaction"
    )
    
    class Meta:
        ordering = ['-priority', '-created_at']
        unique_together = [['company', 'name']]
        verbose_name = "Bank Rule"
        verbose_name_plural = "Bank Rules"
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['-priority']),
        ]
    
    def __str__(self):
        status = "✅" if self.is_active else "❌"
        return f"{status} {self.company.name} - {self.name}"
    
    def increment_match_count(self):
        """Update statistics when rule matches"""
        self.times_matched += 1
        self.last_matched = timezone.now()
        self.save(update_fields=['times_matched', 'last_matched'])


class BankRuleCondition(models.Model):
    """
    Individual condition within a rule (Field + Operator + Value)
    
    Structure: [Field] [Operator] [Value]
    Example: [Description] [Contains] [RENT]
    Example: [Amount] [Greater Than] [1000000]
    """
    
    rule = models.ForeignKey(
        BankRule,
        on_delete=models.CASCADE,
        related_name='conditions'
    )
    
    # Column A: Field to check
    FIELD_CHOICES = [
        ('description', 'Transaction Description'),
        ('amount', 'Amount (Exact)'),
        ('amount_abs', 'Amount (Absolute Value)'),
        ('debit_credit', 'Debit or Credit'),
        ('correspondent_account', 'Correspondent Account'),
        ('date', 'Transaction Date'),
        ('reference', 'Reference Number'),
    ]
    
    field = models.CharField(
        max_length=50,
        choices=FIELD_CHOICES,
        help_text="Which transaction field to check"
    )
    
    # Column B: Comparison operator
    OPERATOR_CHOICES = [
        # Text operators
        ('equals', 'Equals (exact match)'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('not_contains', 'Does Not Contain'),
        ('starts_with', 'Starts With'),
        ('ends_with', 'Ends With'),
        ('is_blank', 'Is Blank/Empty'),
        ('is_not_blank', 'Is Not Blank'),
        
        # Numeric operators
        ('greater_than', 'Greater Than (>)'),
        ('less_than', 'Less Than (<)'),
        ('greater_equal', 'Greater or Equal (≥)'),
        ('less_equal', 'Less or Equal (≤)'),
        ('between', 'Between (range)'),
    ]
    
    operator = models.CharField(
        max_length=50,
        choices=OPERATOR_CHOICES,
        help_text="How to compare the field value"
    )
    
    # Column C: Value(s) to compare against
    value = models.CharField(
        max_length=500,
        blank=True,
        help_text="Primary value (or lower bound for 'between')"
    )
    
    value_secondary = models.CharField(
        max_length=500,
        blank=True,
        help_text="Upper bound for 'between' operator only"
    )
    
    # Case sensitivity for text comparisons
    case_sensitive = models.BooleanField(
        default=False,
        help_text="Match case exactly (usually keep OFF for flexibility)"
    )
    
    order = models.IntegerField(
        default=0,
        help_text="Display order in rule builder"
    )
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Rule Condition"
        verbose_name_plural = "Rule Conditions"
    
    def __str__(self):
        field_display = self.get_field_display()
        operator_display = self.get_operator_display()
        value_str = self.value[:50] if self.value else "(empty)"
        
        if self.operator == 'between' and self.value_secondary:
            return f"{field_display} {operator_display} {self.value} and {self.value_secondary}"
        
        return f"{field_display} {operator_display} {value_str}"
