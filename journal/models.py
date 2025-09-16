from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class Journal(BaseModel):
    """Manual Journal Entry Model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('reversed', 'Reversed'),
    ]
    
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='journals', null=True, blank=True, help_text="Company this journal belongs to")
    
    narration = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Narration",
        help_text="Journal entry description"
    )
    
    reference = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Reference",
        help_text="External reference number"
    )
    
    date = models.DateField(
        verbose_name="Journal Date"
    )
    
    auto_reversing_date = models.DateField(
        blank=True, 
        null=True,
        verbose_name="Auto Reversing Date",
        help_text="Date to automatically reverse this journal"
    )
    
    cash_basis = models.BooleanField(
        default=True,
        verbose_name="Cash Basis",
        help_text="Show on cash basis reports"
    )
    
    amount_mode = models.CharField(
        max_length=50,
        default="No Tax",
        verbose_name="Amount Mode"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Status"
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_journals'
    )
    
    class Meta:
        verbose_name = "Manual Journal"
        verbose_name_plural = "Manual Journals"
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"JE{self.id:04d} - {self.narration or 'No narration'}"
    
    @property
    def total_amount(self):
        """Calculate total debit amount"""
        return sum(line.debit for line in self.lines.all())
    
    @property
    def is_balanced(self):
        """Check if journal is balanced"""
        total_debits = sum(line.debit for line in self.lines.all())
        total_credits = sum(line.credit for line in self.lines.all())
        return abs(total_debits - total_credits) < 0.01


class JournalLine(BaseModel):
    """Journal Entry Line Item"""
    journal = models.ForeignKey(
        Journal, 
        on_delete=models.CASCADE,
        related_name='lines'
    )
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='journal_lines', null=True, blank=True, help_text="Company this journal line belongs to")
    
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Description"
    )
    
    account_code = models.CharField(
        max_length=20,
        verbose_name="Account Code"
    )
    
    tax_rate = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tax Rate"
    )
    
    debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Debit Amount"
    )
    
    credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Credit Amount"
    )
    
    line_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Line Order"
    )
    
    class Meta:
        verbose_name = "Journal Line"
        verbose_name_plural = "Journal Lines"
        ordering = ['line_order']
    
    def __str__(self):
        return f"{self.journal} - {self.account_code} - ${self.debit or self.credit}"
