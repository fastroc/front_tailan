from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

# Choice Constants
DEPRECIATION_METHODS = [
    ('none', 'No depreciation'),
    ('straight_line', 'Straight Line'),
    ('declining_balance', 'Declining balance'),
    ('declining_balance_150', 'Declining balance (150%)'),
    ('declining_balance_200', 'Declining balance (200%)'),
    ('full_purchase', 'Full depreciation at purchase'),
]

AVERAGING_METHODS = [
    ('full_month', 'Full month'),
    ('actual_days', 'Actual days'),
]

BASIS_CHOICES = [
    ('rate', 'Rate'),
    ('effective_life', 'Effective life'),
]

DISPOSAL_METHODS = [
    ('sale', 'Sale'),
    ('trade', 'Trade-in'),
    ('scrap', 'Scrap'),
    ('donation', 'Donation'),
    ('transfer', 'Transfer'),
]

TAX_METHODS = [
    ('', 'Same as book'),
    ('macrs', 'MACRS'),
    ('section179', 'Section 179'),
    ('bonus', 'Bonus Depreciation'),
    ('custom', 'Custom'),
]

STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('registered', 'Registered'),
    ('disposed', 'Disposed'),
    ('sold', 'Sold'),
]

TRANSACTION_TYPES = [
    ('acquisition', 'Acquisition'),
    ('improvement', 'Improvement'),
    ('depreciation', 'Depreciation'),
    ('disposal', 'Disposal'),
    ('revaluation', 'Revaluation'),
]


class AssetType(models.Model):
    """Asset category/type model"""
    name = models.CharField(max_length=100, unique=True, help_text="Asset type name (e.g., Computer Equipment)")
    code = models.CharField(max_length=10, unique=True, help_text="Short code for asset type")
    default_life_years = models.IntegerField(
        default=5, 
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Default useful life in years"
    )
    default_depreciation_method = models.CharField(
        max_length=30, 
        choices=DEPRECIATION_METHODS, 
        default='straight_line',
        help_text="Default depreciation method for this asset type"
    )
    description = models.TextField(blank=True, help_text="Detailed description of asset type")
    is_active = models.BooleanField(default=True, help_text="Whether this asset type is available for new assets")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Asset Type"
        verbose_name_plural = "Asset Types"
    
    def __str__(self):
        return self.name


class FixedAsset(models.Model):
    """Primary Fixed Asset model based on enterprise template analysis"""
    
    # Basic Asset Information (from template Asset Details section)
    name = models.CharField(
        max_length=200, 
        help_text="Asset name (e.g., Dell Laptop)",
        verbose_name="Asset Name"
    )
    number = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Auto-generated asset number",
        verbose_name="Asset Number"
    )
    description = models.TextField(
        blank=True, 
        help_text="Detailed asset description",
        verbose_name="Description"
    )
    asset_type = models.ForeignKey(
        AssetType, 
        on_delete=models.PROTECT,
        help_text="Asset category/type",
        verbose_name="Asset Type"
    )
    serial_number = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Manufacturer serial number",
        verbose_name="Serial Number"
    )
    
    # Location & Tracking (from template Purchase Details)
    location = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Department/Location (e.g., Main Office, IT Department)",
        verbose_name="Location/Department"
    )
    supplier = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Supplier/vendor name",
        verbose_name="Supplier"
    )
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE,
        help_text="Company that owns this asset"
    )
    
    # Financial Information (from template Purchase Details)
    purchase_price = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Original purchase price",
        verbose_name="Purchase Price"
    )
    purchase_date = models.DateField(
        help_text="Date when asset was purchased",
        verbose_name="Purchase Date"
    )
    depreciation_start_date = models.DateField(
        blank=True, 
        null=True,
        help_text="Date when depreciation starts (defaults to purchase date)",
        verbose_name="Depreciation Start Date"
    )
    residual_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Expected value at end of useful life",
        verbose_name="Residual Value"
    )
    cost_limit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum cost threshold for depreciation",
        verbose_name="Cost Limit"
    )
    
    # Depreciation Configuration (from template Depreciation Details)
    depreciation_method = models.CharField(
        max_length=30, 
        choices=DEPRECIATION_METHODS,
        default='straight_line',
        help_text="Method used to calculate depreciation",
        verbose_name="Depreciation Method"
    )
    averaging_method = models.CharField(
        max_length=20, 
        choices=AVERAGING_METHODS,
        default='full_month',
        help_text="Method for handling partial periods",
        verbose_name="Averaging Method"
    )
    depreciation_basis = models.CharField(
        max_length=20, 
        choices=BASIS_CHOICES,
        default='effective_life',
        help_text="Whether to use rate or effective life for calculations",
        verbose_name="Depreciation Basis"
    )
    depreciation_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
        help_text="Depreciation rate as percentage (0.01-100.00)",
        verbose_name="Depreciation Rate (%)"
    )
    effective_life = models.IntegerField(
        blank=True, 
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Asset useful life in years (1-50)",
        verbose_name="Effective Life (Years)"
    )
    
    # Asset Lifecycle (from template Asset Lifecycle Options)
    warranty_expiry = models.DateField(
        blank=True, 
        null=True,
        help_text="Date when warranty expires",
        verbose_name="Warranty Expiry"
    )
    expected_disposal_date = models.DateField(
        blank=True, 
        null=True,
        help_text="Expected date for asset disposal",
        verbose_name="Expected Disposal Date"
    )
    disposal_method = models.CharField(
        max_length=20, 
        choices=DISPOSAL_METHODS, 
        blank=True,
        help_text="Planned method for asset disposal",
        verbose_name="Disposal Method"
    )
    estimated_disposal_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Expected value when disposing asset",
        verbose_name="Estimated Disposal Value"
    )
    
    # Tax Depreciation (from template Tax Depreciation Options)
    separate_tax_depreciation = models.BooleanField(
        default=False,
        help_text="Whether to use separate tax depreciation calculations",
        verbose_name="Use Separate Tax Depreciation"
    )
    tax_depreciation_method = models.CharField(
        max_length=30, 
        choices=TAX_METHODS, 
        blank=True,
        help_text="Tax depreciation method (if different from book)",
        verbose_name="Tax Depreciation Method"
    )
    
    # Status & Metadata
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        help_text="Current status of the asset",
        verbose_name="Status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='created_assets',
        help_text="User who created this asset"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Fixed Asset"
        verbose_name_plural = "Fixed Assets"
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['asset_type', 'status']),
            models.Index(fields=['purchase_date']),
            models.Index(fields=['number']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate asset number and set defaults"""
        if not self.number:
            self.number = self.generate_asset_number()
        
        if not self.depreciation_start_date and self.purchase_date:
            self.depreciation_start_date = self.purchase_date
            
        super().save(*args, **kwargs)
    
    def generate_asset_number(self):
        """Generate unique asset number"""
        prefix = self.asset_type.code if self.asset_type else 'AST'
        year = self.purchase_date.year if self.purchase_date else 2025
        
        # Get next sequence number for this year and type
        last_asset = FixedAsset.objects.filter(
            number__startswith=f"{prefix}-{year}",
            company=self.company
        ).order_by('number').last()
        
        if last_asset:
            try:
                last_num = int(last_asset.number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
            
        return f"{prefix}-{year}-{next_num:04d}"
    
    @property
    def current_book_value(self):
        """Calculate current book value"""
        # This will be implemented in the calculation service
        from .services import DepreciationCalculator
        calculator = DepreciationCalculator()
        return calculator.get_current_book_value(self)
    
    @property
    def total_accumulated_depreciation(self):
        """Get total accumulated depreciation to date"""
        from .services import DepreciationCalculator
        calculator = DepreciationCalculator()
        return calculator.get_accumulated_depreciation(self)


class DepreciationSchedule(models.Model):
    """Stores calculated depreciation schedule for assets"""
    
    asset = models.ForeignKey(
        FixedAsset, 
        on_delete=models.CASCADE, 
        related_name='depreciation_schedules',
        help_text="Associated fixed asset"
    )
    year = models.IntegerField(
        help_text="Depreciation year",
        verbose_name="Year"
    )
    period_start_date = models.DateField(
        help_text="Start date of depreciation period",
        verbose_name="Period Start"
    )
    period_end_date = models.DateField(
        help_text="End date of depreciation period",
        verbose_name="Period End"
    )
    beginning_book_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Book value at beginning of period",
        verbose_name="Beginning Book Value"
    )
    depreciation_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Depreciation amount for this period",
        verbose_name="Depreciation Amount"
    )
    accumulated_depreciation = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Total accumulated depreciation",
        verbose_name="Accumulated Depreciation"
    )
    ending_book_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Book value at end of period",
        verbose_name="Ending Book Value"
    )
    is_tax_schedule = models.BooleanField(
        default=False,
        help_text="Whether this is tax depreciation schedule",
        verbose_name="Tax Schedule"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['asset', 'year', 'is_tax_schedule']
        ordering = ['asset', 'year']
        verbose_name = "Depreciation Schedule"
        verbose_name_plural = "Depreciation Schedules"
        indexes = [
            models.Index(fields=['asset', 'year']),
            models.Index(fields=['period_start_date', 'period_end_date']),
        ]
    
    def __str__(self):
        schedule_type = "Tax" if self.is_tax_schedule else "Book"
        return f"{self.asset.number} - Year {self.year} ({schedule_type})"


class AssetTransaction(models.Model):
    """Tracks all asset-related transactions and movements"""
    
    asset = models.ForeignKey(
        FixedAsset, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        help_text="Associated fixed asset"
    )
    transaction_type = models.CharField(
        max_length=30, 
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction",
        verbose_name="Transaction Type"
    )
    transaction_date = models.DateField(
        help_text="Date of transaction",
        verbose_name="Transaction Date"
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Transaction amount",
        verbose_name="Amount"
    )
    description = models.TextField(
        help_text="Detailed description of transaction",
        verbose_name="Description"
    )
    reference_number = models.CharField(
        max_length=100, 
        blank=True,
        help_text="External reference number",
        verbose_name="Reference Number"
    )
    journal_entry = models.ForeignKey(
        'journal.Journal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Associated journal entry"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        help_text="User who created this transaction"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name = "Asset Transaction"
        verbose_name_plural = "Asset Transactions"
        indexes = [
            models.Index(fields=['asset', 'transaction_type']),
            models.Index(fields=['transaction_date']),
        ]
    
    def __str__(self):
        return f"{self.asset.number} - {self.get_transaction_type_display()} - {self.transaction_date}"


class AssetDisposal(models.Model):
    """Manages end-of-life asset disposal"""
    
    asset = models.OneToOneField(
        FixedAsset, 
        on_delete=models.CASCADE,
        related_name='disposal',
        help_text="Asset being disposed"
    )
    disposal_date = models.DateField(
        help_text="Date of disposal",
        verbose_name="Disposal Date"
    )
    disposal_method = models.CharField(
        max_length=20, 
        choices=DISPOSAL_METHODS,
        help_text="Method of disposal",
        verbose_name="Disposal Method"
    )
    disposal_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Actual disposal value received",
        verbose_name="Disposal Value"
    )
    book_value_at_disposal = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Book value at time of disposal",
        verbose_name="Book Value at Disposal"
    )
    gain_loss_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Gain or loss on disposal (positive = gain, negative = loss)",
        verbose_name="Gain/Loss Amount"
    )
    buyer_details = models.TextField(
        blank=True,
        help_text="Details about buyer or disposal recipient",
        verbose_name="Buyer Details"
    )
    disposal_costs = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Costs incurred for disposal",
        verbose_name="Disposal Costs"
    )
    journal_entry = models.ForeignKey(
        'journal.Journal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Journal entry for disposal transaction"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        help_text="User who processed the disposal"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-disposal_date']
        verbose_name = "Asset Disposal"
        verbose_name_plural = "Asset Disposals"
        indexes = [
            models.Index(fields=['disposal_date']),
            models.Index(fields=['disposal_method']),
        ]
    
    def __str__(self):
        return f"{self.asset.number} - Disposed {self.disposal_date}"
    
    def save(self, *args, **kwargs):
        """Calculate gain/loss on save"""
        if self.disposal_value is not None and self.book_value_at_disposal is not None:
            self.gain_loss_amount = self.disposal_value - self.book_value_at_disposal - self.disposal_costs
        super().save(*args, **kwargs)
