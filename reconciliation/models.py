from django.db import models
from django.contrib.auth.models import User
from coa.models import Account
from bank_accounts.models import BankTransaction
from journal.models import Journal


class ReconciliationSession(models.Model):
    """Tracks each reconciliation session for a bank account - Enhanced"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, limit_choices_to={'account_type': 'Bank'})
    session_name = models.CharField(max_length=200, help_text="Name or description of this reconciliation")
    
    # Enhanced period tracking
    period_start = models.DateField(null=True, blank=True, help_text="Reconciliation period start date")
    period_end = models.DateField(null=True, blank=True, help_text="Reconciliation period end date")
    
    # Balance tracking
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Opening balance")
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Closing balance")
    statement_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Statement ending balance")
    
    # Enhanced status tracking
    status = models.CharField(max_length=20, choices=[
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('balanced', 'Balanced'),
        ('completed', 'Completed'),
        ('locked', 'Locked')
    ], default='in_progress')
    
    # Statistics (will be calculated)
    total_transactions = models.IntegerField(default=0, help_text="Total transactions in this session")
    matched_transactions = models.IntegerField(default=0, help_text="Successfully matched transactions")
    unmatched_transactions = models.IntegerField(default=0, help_text="Unmatched transactions")
    
    # Audit fields
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.account.name} - {self.period_end} ({self.status})"
    
    @property
    def reconciliation_percentage(self):
        """Calculate reconciliation progress percentage"""
        if self.total_transactions > 0:
            return round((self.matched_transactions / self.total_transactions) * 100, 1)
        return 0
    
    @property 
    def is_balanced(self):
        """Check if reconciliation is balanced"""
        return abs(self.statement_balance - self.closing_balance) < 0.01


class TransactionMatch(models.Model):
    """Enhanced model to store WHO/WHAT/WHY/TAX reconciliation data"""
    
    # Core relationships - separate raw data from processed data
    bank_transaction = models.OneToOneField(BankTransaction, on_delete=models.CASCADE, help_text="Raw bank transaction")
    reconciliation_session = models.ForeignKey(ReconciliationSession, on_delete=models.CASCADE)
    
    # WHO/WHAT/WHY/TAX Data (from reconciliation UI)
    contact = models.CharField(max_length=255, blank=True, help_text="WHO - Contact/Payee name")
    gl_account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, help_text="WHAT - Chart of Account for categorization")
    description = models.TextField(blank=True, help_text="WHY - User description/memo for this transaction") 
    tax_rate = models.CharField(max_length=50, blank=True, help_text="TAX - GST/Tax rate applied")
    
    # Match metadata
    match_type = models.CharField(max_length=20, choices=[
        ('manual', 'Manual Match'),
        ('auto', 'Auto Match'),
        ('partial', 'Partial Match'),
        ('bulk', 'Bulk Match')
    ], default='manual')
    
    match_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="Match confidence percentage")
    is_reconciled = models.BooleanField(default=True, help_text="Is this transaction fully reconciled?")
    
    # Auto-created journal link (for accounting integration)
    journal_entry = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True, help_text="Auto-created journal entry")
    
    # Audit trail
    matched_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, help_text="User who made this match")
    matched_at = models.DateTimeField(null=True, blank=True, help_text="When this match was created")
    notes = models.TextField(blank=True, help_text="Additional reconciliation notes")
    
    class Meta:
        unique_together = ['bank_transaction', 'reconciliation_session']
        ordering = ['-matched_at']
        
    def __str__(self):
        description = self.bank_transaction.description[:50]
        if self.gl_account:
            return f"Match: {description} -> {self.gl_account.name}"
        else:
            # Check for splits without triggering extra query if possible
            try:
                split_count = self.splits.count() if hasattr(self, 'splits') else 0
                if split_count > 0:
                    return f"Split Match: {description} -> {split_count} splits"
                else:
                    return f"Match: {description} -> No GL Account"
            except Exception:
                return f"Match: {description} -> Processing..."
    
    @property
    def is_split_transaction(self):
        """Check if this transaction has splits"""
        return self.splits.exists()
    
    @property
    def total_split_amount(self):
        """Calculate total amount across all splits"""
        return self.splits.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def split_balance_status(self):
        """Check if split amounts match bank transaction amount"""
        if not self.is_split_transaction:
            return 'no_splits'
        
        bank_amount = abs(self.bank_transaction.amount)
        split_total = abs(self.total_split_amount)
        difference = abs(bank_amount - split_total)
        
        if difference < 0.01:  # Within 1 cent
            return 'balanced'
        elif split_total < bank_amount:
            return 'under_allocated'
        else:
            return 'over_allocated'
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to be allocated"""
        bank_amount = abs(self.bank_transaction.amount)
        split_total = abs(self.total_split_amount)
        return bank_amount - split_total


class TransactionSplit(models.Model):
    """Enhanced model for split transaction functionality"""
    
    # Parent transaction match
    transaction_match = models.ForeignKey(TransactionMatch, on_delete=models.CASCADE, related_name='splits')
    
    # Split details
    split_number = models.PositiveIntegerField(help_text="Split sequence number (1, 2, 3...)")
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Amount for this split")
    
    # WHO/WHAT/WHY/TAX for this split
    contact = models.CharField(max_length=255, blank=True, help_text="WHO - Contact/Payee for this split")
    gl_account = models.ForeignKey(Account, on_delete=models.CASCADE, help_text="WHAT - GL Account for this split")
    description = models.TextField(blank=True, help_text="WHY - Description for this split")
    tax_rate = models.CharField(max_length=50, blank=True, help_text="TAX - GST/Tax rate for this split")
    
    # Tax calculations
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Tax amount for this split")
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Net amount (amount - tax)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['split_number']
        unique_together = ['transaction_match', 'split_number']
        
    def __str__(self):
        return f"Split {self.split_number}: {self.amount} -> {self.gl_account.name}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate tax amounts on save"""
        from decimal import Decimal
        
        if self.tax_rate and self.amount:
            # Parse tax rate (e.g., "10%" -> 0.10)
            try:
                if self.tax_rate.endswith('%'):
                    rate = Decimal(self.tax_rate[:-1]) / Decimal('100')
                else:
                    rate = Decimal(self.tax_rate) / Decimal('100')
                
                # Calculate tax (assuming tax-inclusive)
                self.tax_amount = self.amount * rate / (Decimal('1') + rate)
                self.net_amount = self.amount - self.tax_amount
            except (ValueError, ZeroDivisionError, TypeError):
                self.tax_amount = Decimal('0')
                self.net_amount = self.amount
        else:
            self.tax_amount = Decimal('0')
            self.net_amount = self.amount
            
        super().save(*args, **kwargs)


class ReconciliationReport(models.Model):
    """Stores reconciliation reports and summaries"""
    reconciliation_session = models.OneToOneField(ReconciliationSession, on_delete=models.CASCADE)
    total_bank_transactions = models.IntegerField(default=0)
    total_reconciled = models.IntegerField(default=0)
    total_unreconciled = models.IntegerField(default=0)
    auto_matched = models.IntegerField(default=0)
    manual_matched = models.IntegerField(default=0)
    report_data = models.JSONField(default=dict, help_text="Detailed report data")
    generated_at = models.DateTimeField(auto_now_add=True)
    
    def reconciliation_percentage(self):
        if self.total_bank_transactions > 0:
            return round((self.total_reconciled / self.total_bank_transactions) * 100, 1)
        return 0
        
    def __str__(self):
        return f"Report for {self.reconciliation_session}"
