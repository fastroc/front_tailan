"""
PRACTICAL LOAN MODULE IMPLEMENTATION GUIDE
==========================================

This guide shows exactly how to implement loan modules in your existing system
following Django best practices and your current multi-company architecture.
"""

# 1. BASE MODEL MIXIN FOR CONSISTENT MULTI-COMPANY SUPPORT
#    Create this in a new file: shared/models.py

from django.db import models
from django.contrib.auth.models import User

class CompanyAwareModel(models.Model):
    """
    Abstract base class for all models that need company isolation.
    Use this for ALL new loan models to ensure consistency.
    """
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        help_text="Company this record belongs to"
    )
    
    class Meta:
        abstract = True

class AuditableModel(models.Model):
    """
    Abstract base class for audit trail functionality.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    
    class Meta:
        abstract = True

class BaseModel(CompanyAwareModel, AuditableModel):
    """
    Ultimate base class combining company awareness and audit trail.
    Use this for ALL loan models.
    """
    class Meta:
        abstract = True

# =============================================================================
# 2. LOAN CORE MODULE IMPLEMENTATION
#    Create new Django app: loans_core
# =============================================================================

# loans_core/models.py
class LoanProduct(BaseModel):
    """Defines loan products (Personal Loan, Business Loan, etc.)"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    
    # Interest settings
    base_interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    min_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2)
    min_term_months = models.IntegerField()
    max_term_months = models.IntegerField()
    
    # Accounting integration
    interest_income_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_products_interest'
    )
    loan_receivable_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_products_receivable'
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'code']
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class LoanApplication(BaseModel):
    """Customer loan applications"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    application_number = models.CharField(max_length=20, unique=True)
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT)
    
    # Customer information
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    customer_address = models.TextField()
    
    # Loan details
    requested_amount = models.DecimalField(max_digits=15, decimal_places=2)
    requested_term_months = models.IntegerField()
    purpose = models.TextField()
    
    # Application status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    
    # Approved terms (may differ from requested)
    approved_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    approved_term_months = models.IntegerField(null=True, blank=True)
    approved_interest_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'application_number']
    
    def __str__(self):
        return f"{self.application_number} - {self.customer_name}"

class LoanAccount(BaseModel):
    """Active loan accounts created from approved applications"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid_off', 'Paid Off'),
        ('defaulted', 'Defaulted'),
        ('written_off', 'Written Off'),
    ]
    
    loan_application = models.OneToOneField(LoanApplication, on_delete=models.PROTECT)
    account_number = models.CharField(max_length=20, unique=True)
    
    # Loan terms
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    term_months = models.IntegerField()
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Loan lifecycle
    disbursement_date = models.DateField()
    first_payment_date = models.DateField()
    maturity_date = models.DateField()
    
    # Current status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2)
    total_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_payment_date = models.DateField(null=True, blank=True)
    
    # Accounting integration - link to your existing COA
    loan_receivable_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_accounts_receivable'
    )
    
    class Meta:
        unique_together = ['company', 'account_number']
    
    def __str__(self):
        return f"{self.account_number} - {self.loan_application.customer_name}"

# =============================================================================
# 3. LOAN REPAYMENT MODULE
#    Create new Django app: loans_repayment
# =============================================================================

# loans_repayment/models.py
class RepaymentSchedule(BaseModel):
    """Payment schedule for each loan"""
    loan_account = models.ForeignKey('loans_core.LoanAccount', on_delete=models.CASCADE)
    payment_number = models.IntegerField()
    due_date = models.DateField()
    
    # Payment breakdown
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Payment status
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['company', 'loan_account', 'payment_number']
        ordering = ['due_date']

class Payment(BaseModel):
    """Actual payments received from customers"""
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ]
    
    loan_account = models.ForeignKey('loans_core.LoanAccount', on_delete=models.CASCADE)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=50, blank=True)
    
    # Integration with your existing bank_accounts
    bank_transaction = models.ForeignKey(
        'bank_accounts.BankTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to bank transaction if applicable"
    )
    
    # Automatic journal entry creation
    journal_entry = models.ForeignKey(
        'journal.Journal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Automatically created journal entry"
    )
    
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        """Automatically create journal entry when payment is saved"""
        super().save(*args, **kwargs)
        if not self.journal_entry:
            self.create_journal_entry()
    
    def create_journal_entry(self):
        """Create corresponding journal entry for this payment"""
        from journal.models import Journal, JournalLine
        
        # Create journal entry
        journal = Journal.objects.create(
            company=self.company,
            date=self.payment_date,
            description=f"Loan payment from {self.loan_account.loan_application.customer_name}",
            created_by=self.created_by
        )
        
        # Dr. Cash/Bank Account
        JournalLine.objects.create(
            company=self.company,
            journal=journal,
            account=self.loan_account.loan_receivable_account,  # This could be bank account
            debit_amount=self.amount,
            description=f"Payment received - {self.reference_number}"
        )
        
        # Cr. Loan Receivable
        JournalLine.objects.create(
            company=self.company,
            journal=journal,
            account=self.loan_account.loan_receivable_account,
            credit_amount=self.amount,
            description=f"Loan payment - {self.loan_account.account_number}"
        )
        
        self.journal_entry = journal
        self.save(update_fields=['journal_entry'])

# =============================================================================
# 4. INTEGRATION WITH YOUR EXISTING SYSTEM
# =============================================================================

# Enhanced bank_accounts/models.py
class BankTransaction(BaseModel):  # Already has company field
    # ... existing fields ...
    
    # Add loan integration
    loan_payment = models.ForeignKey(
        'loans_repayment.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to loan payment if this transaction is a loan payment"
    )

# Enhanced coa/models.py - Add loan-specific account types
class Account(BaseModel):  # Already has company field
    # ... existing fields ...
    
    ACCOUNT_TYPES = [
        # ... existing types ...
        ('loan_receivable', 'Loan Receivable'),
        ('interest_income', 'Interest Income'),
        ('loan_loss_provision', 'Loan Loss Provision'),
    ]

# =============================================================================
# 5. DJANGO ADMIN INTEGRATION
# =============================================================================

# loans_core/admin.py
from django.contrib import admin
from .models import LoanProduct, LoanApplication, LoanAccount

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'base_interest_rate', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'code']

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_number', 'customer_name', 'company', 'status', 'requested_amount', 'submitted_at']
    list_filter = ['company', 'status', 'loan_product']
    search_fields = ['application_number', 'customer_name', 'customer_email']

@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'company', 'status', 'principal_amount', 'current_balance', 'disbursement_date']
    list_filter = ['company', 'status']
    search_fields = ['account_number', 'loan_application__customer_name']

# =============================================================================
# 6. IMPLEMENTATION STEPS
# =============================================================================

"""
STEP-BY-STEP IMPLEMENTATION:

1. Create shared/models.py with base classes
2. Create loans_core Django app
3. Create loans_repayment Django app  
4. Add to INSTALLED_APPS in settings.py
5. Create and run migrations
6. Update existing models with loan integration
7. Test with sample data
8. Add reporting and collections modules

COMMANDS:
django_env\Scripts\python.exe manage.py startapp loans_core
django_env\Scripts\python.exe manage.py startapp loans_repayment
django_env\Scripts\python.exe manage.py makemigrations
django_env\Scripts\python.exe manage.py migrate
"""
