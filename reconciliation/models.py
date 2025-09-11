from django.db import models
from django.contrib.auth.models import User
from coa.models import Account
from bank_accounts.models import BankTransaction
from journal.models import Journal


class ReconciliationSession(models.Model):
    """Tracks each reconciliation session for a bank account"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, limit_choices_to={'account_type': 'Bank'})
    session_name = models.CharField(max_length=200, help_text="Name or description of this reconciliation")
    statement_date = models.DateField(help_text="Statement ending date")
    statement_balance = models.DecimalField(max_digits=15, decimal_places=2, help_text="Statement ending balance")
    reconciled_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Reconciled balance")
    difference = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Difference between statement and reconciled")
    status = models.CharField(max_length=20, choices=[
        ('in_progress', 'In Progress'),
        ('balanced', 'Balanced'),
        ('unbalanced', 'Unbalanced'),
        ('completed', 'Completed')
    ], default='in_progress')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.account.name} - {self.session_name} ({self.statement_date})"


class TransactionMatch(models.Model):
    """Links bank transactions to journal entries during reconciliation"""
    reconciliation_session = models.ForeignKey(ReconciliationSession, on_delete=models.CASCADE)
    bank_transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE)
    journal_entry = models.ForeignKey(Journal, on_delete=models.CASCADE, null=True, blank=True)
    match_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Auto-match confidence %")
    is_manual_match = models.BooleanField(default=False, help_text="Was this match done manually?")
    is_reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reconciled_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Reconciliation notes")
    
    class Meta:
        unique_together = ['bank_transaction', 'reconciliation_session']
        
    def __str__(self):
        return f"Match: {self.bank_transaction} -> {self.journal_entry}"


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
