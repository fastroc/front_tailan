from django.db import models
from core.models import BaseModel, UserTrackingModel
from core.managers import CompanyAwareManager


class AccountType(models.TextChoices):
    """Detailed account type choices for Chart of Accounts."""

    # ASSETS
    CURRENT_ASSET = "CURRENT_ASSET", "Current Asset"
    FIXED_ASSET = "FIXED_ASSET", "Fixed Asset"
    INVENTORY = "INVENTORY", "Inventory"
    NON_CURRENT_ASSET = "NON_CURRENT_ASSET", "Non-current Asset"
    PREPAYMENT = "PREPAYMENT", "Prepayment"

    # EQUITY
    EQUITY = "EQUITY", "Equity"

    # EXPENSES
    DEPRECIATION = "DEPRECIATION", "Depreciation"
    DIRECT_COST = "DIRECT_COST", "Direct Cost"
    EXPENSE = "EXPENSE", "Expense"
    OVERHEAD = "OVERHEAD", "Overhead"

    # LIABILITIES
    CURRENT_LIABILITY = "CURRENT_LIABILITY", "Current Liability"
    LIABILITY = "LIABILITY", "Liability"
    NON_CURRENT_LIABILITY = "NON_CURRENT_LIABILITY", "Non-current Liability"

    # REVENUE
    OTHER_INCOME = "OTHER_INCOME", "Other Income"
    REVENUE = "REVENUE", "Revenue"
    SALES = "SALES", "Sales"

    @classmethod
    def get_grouped_choices(cls):
        """Return choices grouped by main categories"""
        return {
            "ASSETS": [
                (cls.CURRENT_ASSET, "Current Asset"),
                (cls.FIXED_ASSET, "Fixed Asset"),
                (cls.INVENTORY, "Inventory"),
                (cls.NON_CURRENT_ASSET, "Non-current Asset"),
                (cls.PREPAYMENT, "Prepayment"),
            ],
            "EQUITY": [
                (cls.EQUITY, "Equity"),
            ],
            "EXPENSES": [
                (cls.DEPRECIATION, "Depreciation"),
                (cls.DIRECT_COST, "Direct Cost"),
                (cls.EXPENSE, "Expense"),
                (cls.OVERHEAD, "Overhead"),
            ],
            "LIABILITIES": [
                (cls.CURRENT_LIABILITY, "Current Liability"),
                (cls.LIABILITY, "Liability"),
                (cls.NON_CURRENT_LIABILITY, "Non-current Liability"),
            ],
            "REVENUE": [
                (cls.OTHER_INCOME, "Other Income"),
                (cls.REVENUE, "Revenue"),
                (cls.SALES, "Sales"),
            ],
        }


class TaxRate(BaseModel):
    """Tax rate configurations"""

    # Add company field for multi-company support
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        verbose_name="Company",
        help_text="Company this tax rate belongs to",
    )

    name = models.CharField(max_length=100, verbose_name="Tax Rate Name")
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.0000,
        verbose_name="Tax Rate (%)",
        help_text="Enter as decimal (e.g., 0.1500 for 15%)",
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Setup-related fields
    is_default = models.BooleanField(
        default=False,
        verbose_name="Default Tax Rate",
        help_text="Default tax rate for this company",
    )
    setup_created = models.BooleanField(
        default=False,
        verbose_name="Created During Setup",
        help_text="Tax rate created during company setup process",
    )
    is_system_defined = models.BooleanField(
        default=False,
        verbose_name="System Defined",
        help_text="System defined tax rates cannot be deleted",
    )

    # Tax authority information
    tax_authority = models.CharField(
        max_length=100, blank=True, help_text="Tax collection authority"
    )
    tax_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("sales_tax", "Sales Tax"),
            ("vat", "Value Added Tax (VAT)"),
            ("gst", "Goods & Services Tax (GST)"),
            ("excise", "Excise Tax"),
            ("other", "Other"),
        ],
        help_text="Type of tax",
    )

    # Add company-aware manager
    objects = CompanyAwareManager()

    def __str__(self):
        return f"{self.name} ({self.rate * 100:.2f}%)"

    @property
    def percentage_display(self):
        return f"{self.rate * 100:.2f}%"

    def can_be_deleted(self):
        """Check if tax rate can be deleted."""
        # System defined tax rates cannot be deleted
        if self.is_system_defined:
            return False, "You cannot delete system defined tax rates"

        # Check if used by accounts
        account_count = self.account_set.filter(is_active=True).count()
        if account_count > 0:
            return (
                False,
                f"You cannot delete tax rates used on {account_count} account(s)",
            )

        # Check if used by repeating invoices (future feature)
        # repeating_invoice_count = self.repeatinginvoice_set.count()
        # if repeating_invoice_count > 0:
        #     return False, f"You cannot delete tax rates used on repeating invoices"

        return True, ""

    def can_be_edited(self):
        """Check if tax rate can be edited."""
        if self.is_system_defined:
            # System defined rates can only have their status changed
            return True, "limited"  # Limited editing
        return True, "full"  # Full editing

    @staticmethod
    def create_default_tax_rates(company):
        """Create default system tax rates for a new company."""
        # Check if system tax rates already exist for this company
        existing_system_rates = TaxRate.objects.filter(
            company=company, is_system_defined=True
        ).count()

        if existing_system_rates > 0:
            return []  # Already exist, don't create duplicates

        default_rates = [
            {
                "name": "Sales Tax on Imports",
                "rate": 0.0000,
                "description": "Sales tax rate for imported goods",
                "tax_type": "sales_tax",
                "is_system_defined": True,
                "setup_created": True,
            },
            {
                "name": "Tax Exempt",
                "rate": 0.0000,
                "description": "Tax exempt transactions",
                "tax_type": "other",
                "is_system_defined": True,
                "setup_created": True,
            },
            {
                "name": "Tax on Purchases",
                "rate": 0.0000,
                "description": "Default tax rate for purchase transactions",
                "tax_type": "sales_tax",
                "is_system_defined": True,
                "setup_created": True,
            },
            {
                "name": "Tax on Sales",
                "rate": 0.0000,
                "description": "Default tax rate for sales transactions",
                "tax_type": "sales_tax",
                "is_system_defined": True,
                "setup_created": True,
                "is_default": True,  # This will be the default
            },
        ]

        created_rates = []
        for rate_data in default_rates:
            # Double-check each rate doesn't exist by name
            existing_rate = TaxRate.objects.filter(
                company=company, name=rate_data["name"]
            ).first()

            if not existing_rate:
                tax_rate = TaxRate.objects.create(company=company, **rate_data)
                created_rates.append(tax_rate)

        return created_rates

    class Meta:
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"
        ordering = ["company", "name"]
        # Ensure unique tax rate names per company
        unique_together = [["company", "name"]]


class Account(BaseModel, UserTrackingModel):
    """Chart of Accounts - Main account table with all requested fields"""

    # Company relationship for multi-tenancy
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        verbose_name="Company",
        help_text="Company this account belongs to",
    )

    # Core account information
    code = models.CharField(
        max_length=10,
        verbose_name="Code",
        help_text="A unique code/number for this account (limited to 10 characters)",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Name",
        help_text="A short title for this account (limited to 150 characters)",
    )
    account_type = models.CharField(
        max_length=25, choices=AccountType.choices, verbose_name="Account Type"
    )

    # Tax configuration
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Tax",
        help_text="The default tax setting for this account",
    )

    # Setup-related fields
    is_essential = models.BooleanField(
        default=False,
        verbose_name="Essential Account",
        help_text="Account created during essential setup process",
    )
    setup_category = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("cash", "Cash Account"),
            ("income", "Income Account"),
            ("expense", "Expense Account"),
            ("equity", "Equity Account"),
        ],
        help_text="Setup category for essential accounts",
    )

    # Balance tracking
    opening_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Opening Balance",
        help_text="Opening balance for this account",
    )
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Current Balance",
        help_text="Current balance for this account",
    )

    # Additional information
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
        help_text="A description of how this account should be used (optional)",
    )

    # Financial tracking
    ytd_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="YTD Balance",
        help_text="Year-to-Date balance amount",
    )

    # Account control
    is_locked = models.BooleanField(
        default=False,
        verbose_name="Is Locked",
        help_text="Locked accounts cannot be modified",
    )

    is_active = models.BooleanField(
        default=True, verbose_name="Is Active", help_text="Inactive accounts are hidden"
    )

    # Bank account designation
    is_bank_account = models.BooleanField(
        default=False,
        verbose_name="Is Bank Account",
        help_text="Mark this CURRENT_ASSET account as a bank account for bank management features"
    )

    # Hierarchy
    parent_account = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Parent Account",
        help_text="For sub-accounts",
    )

    # Add company-aware manager
    objects = CompanyAwareManager()

    class Meta:
        verbose_name = "Chart of Account"
        verbose_name_plural = "Chart of Accounts"
        ordering = ["company", "code", "name"]
        indexes = [
            models.Index(fields=["company", "code"]),
            models.Index(fields=["company", "account_type"]),
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "is_essential", "setup_category"]),
            models.Index(fields=["company", "tax_rate"]),
        ]
        # Ensure unique codes per company
        unique_together = [["company", "code"]]

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

    def is_setup_essential(self):
        """Check if this is an essential setup account"""
        return self.is_essential and self.setup_category in [
            "cash",
            "income",
            "expense",
        ]


class OpeningBalance(BaseModel, UserTrackingModel):
    """Opening balance entries for accounts during setup"""

    # Company relationship for multi-tenancy
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        verbose_name="Company",
        help_text="Company this opening balance belongs to",
    )

    # Account relationship
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        verbose_name="Account",
        help_text="Account for this opening balance",
    )

    # Balance information
    balance_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Balance Amount",
        help_text="Opening balance amount",
    )

    balance_date = models.DateField(
        verbose_name="Balance Date", help_text="Date of the opening balance"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
        help_text="Optional description for the opening balance",
    )

    # Audit trail
    entered_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        verbose_name="Entered By",
        help_text="User who entered this opening balance",
    )

    entered_at = models.DateTimeField(auto_now_add=True, verbose_name="Entered At")

    is_active = models.BooleanField(
        default=True, verbose_name="Is Active", help_text="Active opening balances"
    )

    # Add company-aware manager
    objects = CompanyAwareManager()

    class Meta:
        verbose_name = "Opening Balance"
        verbose_name_plural = "Opening Balances"
        ordering = ["company", "account__code", "balance_date"]
        indexes = [
            models.Index(fields=["company", "account"]),
            models.Index(fields=["company", "balance_date"]),
            models.Index(fields=["company", "is_active"]),
        ]
        # One opening balance per account per company
        unique_together = [["company", "account"]]

    def __str__(self):
        return f"{self.account.full_name} - ${self.balance_amount:,.2f}"

    @property
    def formatted_amount(self):
        """Return formatted balance amount"""
        return f"${self.balance_amount:,.2f}"

    @property
    def account_code(self):
        """Return account code for easy reference"""
        return self.account.code

    @property
    def account_name(self):
        """Return account name for easy reference"""
        return self.account.name

    def save(self, *args, **kwargs):
        """Override save to update account opening balance"""
        super().save(*args, **kwargs)
        # Update the related account's opening balance
        if self.is_active:
            self.account.opening_balance = self.balance_amount
            self.account.current_balance = self.balance_amount
            self.account.save(update_fields=["opening_balance", "current_balance"])
