"""
RECOMMENDED: Enhanced Reconciliation Data Structure

This structure supports the WHO/WHAT/WHY/TAX workflow from your reconciliation UI
while maintaining flexibility for future enhancements.
"""

class TransactionMatch(models.Model):
    """Enhanced model to store complete reconciliation data"""
    
    # Core relationships
    reconciliation_session = models.ForeignKey(ReconciliationSession, on_delete=models.CASCADE)
    bank_transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE)
    
    # WHO/WHAT/WHY/TAX Data (from your reconciliation UI)
    contact = models.CharField(max_length=255, blank=True, help_text="WHO - Contact/Payee")
    gl_account = models.ForeignKey('coa.Account', on_delete=models.CASCADE, help_text="WHAT - Chart of Account")
    description = models.TextField(blank=True, help_text="WHY - User description/memo") 
    tax_rate = models.CharField(max_length=50, blank=True, help_text="TAX - GST/Tax rate")
    
    # Match metadata
    match_type = models.CharField(max_length=20, choices=[
        ('manual', 'Manual Match'),
        ('auto', 'Auto Match'),
        ('partial', 'Partial Match'),
        ('split', 'Split Match')
    ], default='manual')
    
    match_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    is_reconciled = models.BooleanField(default=True)
    
    # Audit trail
    reconciled_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reconciled_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    # Optional journal link (for advanced users)
    journal_entry = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['bank_transaction', 'reconciliation_session']
        
    def __str__(self):
        return f"Match: {self.bank_transaction.description} -> {self.gl_account.name}"


class ReconciliationSession(models.Model):
    """Enhanced session tracking"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, limit_choices_to={'account_type': 'Bank'})
    session_name = models.CharField(max_length=200, help_text="Auto-generated or custom name")
    
    # Period and balances
    period_start = models.DateField(help_text="Reconciliation period start")
    period_end = models.DateField(help_text="Reconciliation period end")
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    statement_balance = models.DecimalField(max_digits=15, decimal_places=2, help_text="Final statement balance")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=[
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('balanced', 'Balanced'),
        ('completed', 'Completed'),
        ('locked', 'Locked')
    ], default='in_progress')
    
    # Statistics (calculated fields)
    total_transactions = models.IntegerField(default=0)
    matched_transactions = models.IntegerField(default=0) 
    unmatched_transactions = models.IntegerField(default=0)
    
    # Timestamps
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def reconciliation_percentage(self):
        if self.total_transactions > 0:
            return round((self.matched_transactions / self.total_transactions) * 100, 1)
        return 0
    
    @property 
    def is_balanced(self):
        return abs(self.statement_balance - self.closing_balance) < 0.01
        
    def __str__(self):
        return f"{self.account.name} - {self.period_end} ({self.status})"
