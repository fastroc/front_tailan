from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from company.models import Company
from coa.models import Account


class ConversionDate(models.Model):
    """Stores the conversion date for transitioning to the new accounting system"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE,
        related_name='conversion_date'
    )
    conversion_date = models.DateField(
        help_text="Date when you began processing transactions in this system"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Conversion Date"
        verbose_name_plural = "Conversion Dates"
        
    def __str__(self):
        return f"{self.company.name} - Conversion Date: {self.conversion_date}"
    
    @property
    def as_at_date(self):
        """Returns the last day of the month before conversion date"""
        from datetime import timedelta
        conv_date = self.conversion_date
        # Get last day of previous month
        first_day = conv_date.replace(day=1)
        as_at = first_day - timedelta(days=1)
        return as_at


class ConversionBalance(models.Model):
    """Stores opening balances for accounts during system conversion"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='conversion_balances'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='conversion_balances'
    )
    as_at_date = models.DateField(
        help_text="Date for which this opening balance is valid"
    )
    debit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Debit opening balance"
    )
    credit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Credit opening balance"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this opening balance"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Conversion Balance"
        verbose_name_plural = "Conversion Balances"
        unique_together = ['company', 'account', 'as_at_date']
        ordering = ['account__code', 'account__name']
        
    def __str__(self):
        return f"{self.account.code} - {self.account.name} ({self.as_at_date})"
    
    @property
    def net_amount(self):
        """Returns the net amount (debit - credit)"""
        return self.debit_amount - self.credit_amount
    
    @property
    def balance_type(self):
        """Returns whether this is a debit or credit balance"""
        if self.debit_amount > self.credit_amount:
            return "Debit"
        elif self.credit_amount > self.debit_amount:
            return "Credit"
        else:
            return "Zero"
    
    def clean(self):
        """Ensure either debit or credit is entered, but not both"""
        from django.core.exceptions import ValidationError
        
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError("Enter either debit OR credit amount, not both.")
        
        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValidationError("Enter either a debit or credit amount.")


class ConversionPeriod(models.Model):
    """Predefined periods for conversion balance entry"""
    PERIOD_CHOICES = [
        ('current_year', 'Current Year'),
        ('previous_year', 'Previous Year'),
        ('last_6_months', 'Last 6 Months'),
        ('last_3_months', 'Last 3 Months'),
        ('custom', 'Custom Period'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='conversion_periods'
    )
    name = models.CharField(max_length=100)
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Conversion Period"
        verbose_name_plural = "Conversion Periods"
        ordering = ['-is_active', 'start_date']
        
    def __str__(self):
        return f"{self.company.name} - {self.name} ({self.start_date} to {self.end_date})"
