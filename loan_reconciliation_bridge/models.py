"""
Models for loan_reconciliation_bridge app
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class LoanGLConfiguration(models.Model):
    """
    Configuration for GL accounts used in loan payment calculations
    Each company can have its own GL account mapping
    """
    company = models.OneToOneField(
        'company.Company',
        on_delete=models.CASCADE,
        related_name='loan_gl_config'
    )
    
    # GL Accounts for loan payment allocation
    principal_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_principal_configs',
        help_text='Account for loan principal payments (e.g., 1200 - Loans Receivable)'
    )
    
    interest_income_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_interest_configs',
        null=True,
        blank=True,
        help_text='Account for interest income (e.g., 4200 - Interest Income) - Optional'
    )
    
    late_fee_income_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_late_fee_configs',
        null=True,
        blank=True,
        help_text='Account for late fee income (e.g., 4250 - Late Fee Income) - Optional'
    )
    
    # Additional fields from existing migration
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this configuration is currently active'
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who created this configuration'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Loan GL Configuration'
        verbose_name_plural = 'Loan GL Configurations'
        
    def __str__(self):
        return f'Loan GL Config for {self.company.name}'
        
    def clean(self):
        """Validate that all accounts belong to the same company"""
        if self.company_id:
            accounts = [self.principal_account]
            # Add optional accounts if they exist
            if self.interest_income_account:
                accounts.append(self.interest_income_account)
            if self.late_fee_income_account:
                accounts.append(self.late_fee_income_account)
                
            for account in accounts:
                if account and account.company_id != self.company_id:
                    raise ValidationError(
                        f'Account {account.code} - {account.name} does not belong to company {self.company.name}'
                    )


class LoanCalculationLog(models.Model):
    """
    Audit log for loan payment calculations
    Tracks all calculations performed by the bridge service
    """
    company = models.ForeignKey(
        'company.Company',
        on_delete=models.CASCADE,
        related_name='loan_calculation_logs'
    )
    
    # Customer and loan information  
    customer_name = models.CharField(
        max_length=200,
        help_text='Name of customer for loan payment'
    )
    
    # Payment calculation details
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total payment amount'
    )
    late_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Late fee portion of payment'
    )
    interest_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Interest portion of payment'
    )
    principal_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Principal portion of payment'
    )
    
    # Calculation metadata
    calculation_source = models.CharField(
        max_length=50,
        default='loan_bridge_service',
        help_text='Source system that performed the calculation'
    )
    success = models.BooleanField(
        default=True,
        help_text='Whether the calculation was successful'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error message if calculation failed'
    )
    
    # Additional fields from existing migration
    calculated_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this calculation was performed'
    )
    calculated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who triggered this calculation'
    )
    gl_configuration = models.ForeignKey(
        'LoanGLConfiguration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='GL configuration used for this calculation'
    )
    
    class Meta:
        verbose_name = 'Loan Calculation Log'
        verbose_name_plural = 'Loan Calculation Logs'
        ordering = ['-calculated_at']
        
    def __str__(self):
        return f'Calculation for {self.customer_name} - ${self.payment_amount} ({self.calculated_at.strftime("%Y-%m-%d")})'
