from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from decimal import Decimal
import uuid

class CollateralType(models.Model):
    """Defines the types of collateral that can be accepted"""
    
    CATEGORY_CHOICES = [
        ('real_estate', 'Real Estate'),
        ('vehicle', 'Vehicle'),
        ('equipment', 'Equipment & Machinery'),
        ('securities', 'Securities & Investments'),
        ('inventory', 'Inventory & Stock'),
        ('cash_deposit', 'Cash Deposit'),
        ('other', 'Other Assets'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('very_high', 'Very High Risk'),
    ]
    
    name = models.CharField(max_length=100, help_text="Type name (e.g., 'Residential Property')")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)
    
    # Valuation parameters
    max_loan_to_value = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('80.00'),
        help_text="Maximum LTV ratio as percentage (e.g., 80.00 for 80%)"
    )
    depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Annual depreciation rate as percentage"
    )
    
    # Risk assessment
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='medium')
    liquidity_score = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Liquidity score (1=Very Illiquid, 10=Very Liquid)"
    )
    
    # Operational
    is_active = models.BooleanField(default=True)
    requires_insurance = models.BooleanField(default=False)
    requires_professional_valuation = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Collateral Type"
        verbose_name_plural = "Collateral Types"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class Collateral(models.Model):
    """Individual collateral items linked to loan applications"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('valued', 'Professionally Valued'),
        ('approved', 'Approved for Collateral'),
        ('rejected', 'Rejected'),
        ('released', 'Released'),
    ]
    
    CONDITION_CHOICES = [
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ]
    
    # Identifiers
    collateral_id = models.CharField(max_length=20, unique=True, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Relationships
    loan_application = models.ForeignKey(
        'loans_core.LoanApplication', 
        on_delete=models.CASCADE,
        related_name='collateral_items'
    )
    collateral_type = models.ForeignKey(CollateralType, on_delete=models.PROTECT)
    
    # Basic Information
    title = models.CharField(max_length=200, help_text="Brief title describing the collateral")
    description = models.TextField(help_text="Detailed description of the collateral item")
    
    # Physical Details
    location = models.CharField(max_length=500, blank=True, null=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    
    # Vehicle-specific fields (optional, used when collateral_type.category == 'vehicle')
    vehicle_make = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle manufacturer (e.g., Toyota, BMW)")
    vehicle_model = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle model (e.g., Camry, X5)")
    vehicle_year = models.IntegerField(blank=True, null=True, help_text="Year of manufacture")
    vehicle_registration_year = models.IntegerField(blank=True, null=True, help_text="Year of first registration")
    vehicle_license_plate = models.CharField(max_length=50, blank=True, null=True, help_text="License plate number")
    vehicle_vin = models.CharField(max_length=50, blank=True, null=True, help_text="Vehicle Identification Number (VIN)")
    vehicle_mileage = models.IntegerField(blank=True, null=True, help_text="Current mileage/odometer reading")
    vehicle_fuel_type = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[
            ('gasoline', 'Gasoline'),
            ('diesel', 'Diesel'),
            ('hybrid', 'Hybrid'),
            ('electric', 'Electric'),
            ('cng', 'CNG'),
            ('lpg', 'LPG'),
        ],
        help_text="Type of fuel used"
    )
    
    # Ownership & Legal
    owner_name = models.CharField(max_length=200)
    ownership_document = models.CharField(max_length=500, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Valuation
    declared_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Value declared by applicant"
    )
    market_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Current market value assessment"
    )
    loan_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Value acceptable for loan calculation (after LTV ratio)"
    )
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_date = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='verified_collateral'
    )
    
    # Insurance
    insurance_required = models.BooleanField(default=False)
    insurance_policy_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_expiry_date = models.DateField(blank=True, null=True)
    insurance_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Collateral"
        verbose_name_plural = "Collateral Items"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.collateral_id:
            # Generate unique collateral ID
            last_collateral = Collateral.objects.filter(
                collateral_id__startswith='COL'
            ).order_by('-id').first()
            
            if last_collateral:
                try:
                    last_number = int(last_collateral.collateral_id[3:])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            
            self.collateral_id = f"COL{new_number:06d}"
        
        # Auto-calculate loan value based on market value and LTV
        if self.market_value and self.collateral_type:
            ltv_ratio = self.collateral_type.max_loan_to_value / 100
            self.loan_value = self.market_value * ltv_ratio
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.collateral_id} - {self.title}"
    
    def get_absolute_url(self):
        return reverse('loans_collateral:detail', kwargs={'pk': self.pk})
    
    @property 
    def loan_to_value_ratio(self):
        """Calculate current LTV ratio"""
        if self.market_value and self.loan_value:
            return (self.loan_value / self.market_value) * 100
        return 0
    
    @property
    def risk_indicator(self):
        """Get risk level from collateral type"""
        return self.collateral_type.risk_level if self.collateral_type else 'unknown'
    
    @property
    def value_adequacy(self):
        """Assess if collateral value is adequate for loan"""
        if not (self.loan_value and self.loan_application):
            return 'unknown'
        
        required_amount = self.loan_application.requested_amount or 0
        if self.loan_value >= required_amount:
            return 'adequate'
        elif self.loan_value >= required_amount * 0.8:
            return 'marginal'
        else:
            return 'inadequate'


class CollateralValuation(models.Model):
    """Professional valuations for collateral items"""
    
    VALUATION_TYPE_CHOICES = [
        ('initial', 'Initial Valuation'),
        ('annual_review', 'Annual Review'),
        ('market_update', 'Market Update'),
        ('damage_assessment', 'Damage Assessment'),
        ('disposal', 'Disposal Valuation'),
    ]
    
    VALUER_TYPE_CHOICES = [
        ('internal', 'Internal Valuation'),
        ('external', 'External Professional'),
        ('automated', 'Automated System'),
    ]
    
    # Relationships
    collateral = models.ForeignKey(
        Collateral, 
        on_delete=models.CASCADE,
        related_name='valuations'
    )
    
    # Valuation Details
    valuation_type = models.CharField(max_length=20, choices=VALUATION_TYPE_CHOICES)
    valuer_type = models.CharField(max_length=20, choices=VALUER_TYPE_CHOICES)
    valuer_name = models.CharField(max_length=200)
    valuer_license = models.CharField(max_length=100, blank=True, null=True)
    
    # Values
    assessed_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    forced_sale_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Estimated value in forced sale scenario"
    )
    
    # Report Details
    valuation_date = models.DateField()
    report_reference = models.CharField(max_length=100, blank=True, null=True)
    methodology = models.TextField(blank=True, null=True)
    key_assumptions = models.TextField(blank=True, null=True)
    limitations = models.TextField(blank=True, null=True)
    
    # Validity
    valid_until = models.DateField(help_text="Valuation validity expiry date")
    is_current = models.BooleanField(default=True)
    
    # Attachments
    report_file = models.FileField(
        upload_to='collateral/valuations/', 
        blank=True, 
        null=True,
        help_text="Upload valuation report PDF"
    )
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Collateral Valuation"
        verbose_name_plural = "Collateral Valuations"
        ordering = ['-valuation_date']
    
    def save(self, *args, **kwargs):
        # Update collateral market value with latest valuation
        super().save(*args, **kwargs)
        if self.is_current:
            self.collateral.market_value = self.assessed_value
            self.collateral.save()
            
            # Mark other valuations for this collateral as not current
            CollateralValuation.objects.filter(
                collateral=self.collateral
            ).exclude(
                pk=self.pk
            ).update(is_current=False)
    
    def __str__(self):
        return f"{self.collateral.collateral_id} - {self.get_valuation_type_display()} ({self.valuation_date})"


class CollateralDocument(models.Model):
    """Documents related to collateral items"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('ownership', 'Ownership Certificate'),
        ('title_deed', 'Title Deed'),
        ('registration', 'Registration Document'),
        ('insurance', 'Insurance Policy'),
        ('valuation', 'Valuation Report'),
        ('photos', 'Photographs'),
        ('inspection', 'Inspection Report'),
        ('legal_opinion', 'Legal Opinion'),
        ('other', 'Other Document'),
    ]
    
    # Relationships
    collateral = models.ForeignKey(
        Collateral,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    # Document Details
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # File Details
    file = models.FileField(upload_to='collateral/documents/')
    file_size = models.IntegerField(blank=True, null=True, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    
    # Validity
    document_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    # Audit
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Collateral Document"
        verbose_name_plural = "Collateral Documents"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.collateral.collateral_id} - {self.get_document_type_display()}"
    
    @property
    def is_expired(self):
        """Check if document has expired"""
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False
