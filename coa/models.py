from django.db import models
from core.models import BaseModel, UserTrackingModel


class AccountType(models.TextChoices):
    """Detailed account type choices for Chart of Accounts."""
    # ASSETS
    CURRENT_ASSET = 'CURRENT_ASSET', 'Current Asset'
    FIXED_ASSET = 'FIXED_ASSET', 'Fixed Asset'
    INVENTORY = 'INVENTORY', 'Inventory'
    NON_CURRENT_ASSET = 'NON_CURRENT_ASSET', 'Non-current Asset'
    PREPAYMENT = 'PREPAYMENT', 'Prepayment'
    
    # EQUITY
    EQUITY = 'EQUITY', 'Equity'
    
    # EXPENSES
    DEPRECIATION = 'DEPRECIATION', 'Depreciation'
    DIRECT_COST = 'DIRECT_COST', 'Direct Cost'
    EXPENSE = 'EXPENSE', 'Expense'
    OVERHEAD = 'OVERHEAD', 'Overhead'
    
    # LIABILITIES
    CURRENT_LIABILITY = 'CURRENT_LIABILITY', 'Current Liability'
    LIABILITY = 'LIABILITY', 'Liability'
    NON_CURRENT_LIABILITY = 'NON_CURRENT_LIABILITY', 'Non-current Liability'
    
    # REVENUE
    OTHER_INCOME = 'OTHER_INCOME', 'Other Income'
    REVENUE = 'REVENUE', 'Revenue'
    SALES = 'SALES', 'Sales'

    @classmethod
    def get_grouped_choices(cls):
        """Return choices grouped by main categories"""
        return {
            'ASSETS': [
                (cls.CURRENT_ASSET, 'Current Asset'),
                (cls.FIXED_ASSET, 'Fixed Asset'),
                (cls.INVENTORY, 'Inventory'),
                (cls.NON_CURRENT_ASSET, 'Non-current Asset'),
                (cls.PREPAYMENT, 'Prepayment'),
            ],
            'EQUITY': [
                (cls.EQUITY, 'Equity'),
            ],
            'EXPENSES': [
                (cls.DEPRECIATION, 'Depreciation'),
                (cls.DIRECT_COST, 'Direct Cost'),
                (cls.EXPENSE, 'Expense'),
                (cls.OVERHEAD, 'Overhead'),
            ],
            'LIABILITIES': [
                (cls.CURRENT_LIABILITY, 'Current Liability'),
                (cls.LIABILITY, 'Liability'),
                (cls.NON_CURRENT_LIABILITY, 'Non-current Liability'),
            ],
            'REVENUE': [
                (cls.OTHER_INCOME, 'Other Income'),
                (cls.REVENUE, 'Revenue'),
                (cls.SALES, 'Sales'),
            ],
        }


class TaxRate(BaseModel):
    """Tax rate configurations"""
    name = models.CharField(max_length=100, verbose_name="Tax Rate Name")
    rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=0.0000,
        verbose_name="Tax Rate (%)",
        help_text="Enter as decimal (e.g., 0.1500 for 15%)"
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.rate * 100:.2f}%)"
    
    @property
    def percentage_display(self):
        return f"{self.rate * 100:.2f}%"
    
    class Meta:
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"
        ordering = ['name']


class Account(BaseModel, UserTrackingModel):
    """Chart of Accounts - Main account table with all requested fields"""
    
    # Core account information
    code = models.CharField(
        max_length=10, 
        unique=True, 
        verbose_name="Code",
        help_text="A unique code/number for this account (limited to 10 characters)"
    )
    name = models.CharField(
        max_length=150, 
        verbose_name="Name",
        help_text="A short title for this account (limited to 150 characters)"
    )
    account_type = models.CharField(
        max_length=25,
        choices=AccountType.choices,
        verbose_name="Account Type"
    )
    
    # Tax configuration
    tax_rate = models.ForeignKey(
        TaxRate, 
        on_delete=models.PROTECT,
        verbose_name="Tax",
        help_text="The default tax setting for this account"
    )
    
    # Additional information
    description = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Description",
        help_text="A description of how this account should be used (optional)"
    )
    
    # Financial tracking
    ytd_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.00,
        verbose_name="YTD Balance",
        help_text="Year-to-Date balance amount"
    )
    
    # Account control
    is_locked = models.BooleanField(
        default=False,
        verbose_name="Is Locked",
        help_text="Locked accounts cannot be modified"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Inactive accounts are hidden"
    )
    
    # Hierarchy
    parent_account = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Parent Account",
        help_text="For sub-accounts"
    )
    
    # Additional information
    description = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Description"
    )

    class Meta:
        verbose_name = "Chart of Account"
        verbose_name_plural = "Chart of Accounts"
        ordering = ['code', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['account_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def formatted_ytd_balance(self):
        """Return formatted YTD balance"""
        return f"${self.ytd_balance:,.2f}"

    @property
    def tax_rate_display(self):
        """Return formatted tax rate"""
        return f"{self.tax_rate.name} ({self.tax_rate.rate * 100:.2f}%)"

    @property
    def full_name(self):
        """Return full account name with code"""
        return f"{self.code} - {self.name}"

    @property
    def lock_status(self):
        """Return lock status display"""
        return "🔒 Locked" if self.is_locked else "🔓 Unlocked"

    def can_be_deleted(self):
        """Check if account can be deleted"""
        return not self.is_locked and not self.get_children().exists()

    def get_children(self):
        """Get all child accounts"""
        return Account.objects.filter(parent_account=self)

    def get_hierarchy_level(self):
        """Calculate hierarchy level"""
        level = 0
        parent = self.parent_account
        while parent:
            level += 1
            parent = parent.parent_account
        return level
