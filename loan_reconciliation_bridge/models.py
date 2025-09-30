"""
Models for loan_reconciliation_bridge app
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class LoanGLConfiguration(models.Model):
    """
    Configuration for GL accounts used in loan payment calculations.
    
    Five-Account Structure:
    1. General Loans Receivable (122000) - Main account that creates Payment records via reconciliation
    2. Interest Income Account - Revenue account for interest allocation 
    3. Late Fee Income Account - Revenue account for late fee allocation
    4. Principal Account - Asset account for principal allocation (can be same as #1 or separate)
    5. General Loan Disbursements (1250) - Account for automatic loan disbursement detection and matching
    
    Payment Flow:
    - Reconciliation creates Payment records when transactions hit General Loans Receivable
    - Manager approval splits the payment amount into the three allocation accounts
    - Loan disbursements are automatically detected and matched to General Loan Disbursements account
    - Chart of Accounts balances are updated for detailed financial tracking
    """
    company = models.OneToOneField(
        'company.Company',
        on_delete=models.CASCADE,
        related_name='loan_gl_config'
    )
    
    # Main General Loans Receivable Account (creates Payment records)
    general_loans_receivable_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_main_receivable_configs',
        null=True,  # Temporarily nullable for migration
        blank=True, # Temporarily optional for migration
        help_text='Main account (122000) that receives loan payments and creates Payment records via reconciliation'
    )
    
    # Three-Tier Allocation Accounts (used for manager-approved splits)
    
    # GL Account for principal portion (Asset account)
    principal_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_principal_configs',
        null=True,
        blank=True,
        help_text='Asset account for principal payments (can be same as General Loans Receivable or separate)'
    )
    
    interest_income_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_interest_configs',
        null=True,
        blank=True,
        help_text='Revenue account for interest income (e.g., 4200 - Interest Income)'
    )
    
    late_fee_income_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_late_fee_configs',
        null=True,
        blank=True,
        help_text='Revenue account for late fee income (e.g., 4250 - Late Fee Income)'
    )
    
    # NEW: General Loan Disbursements Account (for auto-matching loan disbursements)
    general_loan_disbursements_account = models.ForeignKey(
        'coa.Account',
        on_delete=models.PROTECT,
        related_name='loan_disbursement_configs',
        null=True,
        blank=True,
        help_text='Account for automatic loan disbursement detection and matching (e.g., 1250 - Loan Disbursements)'
    )
    
    # Configuration settings
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this configuration is currently active'
    )
    
    setup_completed = models.BooleanField(
        default=False,
        help_text='Whether the three-tier setup has been completed'
    )
    
    # Default allocation percentages
    default_interest_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        default=Decimal('30.00'),
        help_text='Default percentage for interest allocation (0-100)'
    )
    
    default_late_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('10.00'), 
        help_text='Default percentage for late fee allocation (0-100)'
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
            accounts = [self.general_loans_receivable_account]
            # Add optional accounts if they exist
            if self.principal_account:
                accounts.append(self.principal_account)
            if self.interest_income_account:
                accounts.append(self.interest_income_account)
            if self.late_fee_income_account:
                accounts.append(self.late_fee_income_account)
            if self.general_loan_disbursements_account:
                accounts.append(self.general_loan_disbursements_account)
                
            for account in accounts:
                if account and account.company_id != self.company_id:
                    raise ValidationError(
                        f'Account {account.code} - {account.name} does not belong to company {self.company.name}'
                    )
    
    def is_three_tier_complete(self):
        """Check if three-tier allocation setup is complete (core functionality)"""
        return (self.general_loans_receivable_account and 
                self.interest_income_account and 
                self.late_fee_income_account and
                self.principal_account)
    
    def is_five_tier_complete(self):
        """Check if full five-tier setup is complete (including disbursements)"""
        return (self.is_three_tier_complete() and 
                self.general_loan_disbursements_account)
    
    def get_main_receivable_account(self):
        """Get the main account that creates Payment records (122000)"""
        return self.general_loans_receivable_account
    
    def get_disbursement_account(self):
        """Get the account for loan disbursement auto-matching (1250)"""
        return self.general_loan_disbursements_account


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
