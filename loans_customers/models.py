from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal
from loans_core.base_models import BaseLoanModel, CompanyAwareLoanModel

class Customer(BaseLoanModel):
    """Customer information for loan applications - Company separated"""
    
    CUSTOMER_TYPE = [
        ('individual', 'Individual'),
        ('business', 'Business/Corporate'),
    ]
    
    EMPLOYMENT_TYPE = [
        ('full_time', 'Full Time Employee'),
        ('part_time', 'Part Time Employee'),
        ('self_employed', 'Self Employed'),
        ('business_owner', 'Business Owner'),
        ('retired', 'Retired'),
        ('unemployed', 'Unemployed'),
        ('student', 'Student'),
    ]
    
    MARITAL_STATUS = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
    ]
    
    # Identifiers
    customer_id = models.CharField(max_length=20, editable=False)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE, default='individual')
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True, help_text="Required for individuals")
    national_id = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^[0-9A-Za-z\-]+$',
            message='National ID must contain only numbers, letters, and dashes'
        )]
    )
    
    # Contact Information
    email = models.EmailField()
    phone_primary = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?[\d\s\-\(\)]+$',
            message='Enter a valid phone number'
        )]
    )
    phone_secondary = models.CharField(
        max_length=20, 
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^\+?[\d\s\-\(\)]+$',
            message='Enter a valid phone number'
        )]
    )
    
    # Address Information
    street_address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    
    # Employment & Income (for individuals)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, blank=True, null=True)
    employer_name = models.CharField(max_length=200, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    employment_duration_months = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    monthly_income = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Gross monthly income"
    )
    other_income = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Other monthly income sources"
    )
    
    # Personal Details (for individuals)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS, blank=True, null=True)
    dependents_count = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Business Information (for business customers)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_registration_number = models.CharField(max_length=50, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    years_in_business = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    annual_revenue = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Financial Information
    monthly_expenses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    existing_debt_payments = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monthly payments on existing debts"
    )
    credit_score = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(300), MinValueValidator(850)]
    )
    
    # Banking Information
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    routing_number = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(
        max_length=20, 
        choices=[('checking', 'Checking'), ('savings', 'Savings')],
        blank=True
    )
    
    # Customer Status
    is_active = models.BooleanField(default=True)
    risk_rating = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('unrated', 'Not Rated'),
        ],
        default='unrated'
    )
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    emergency_contact_phone = models.CharField(
        max_length=20, 
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?[\d\s\-\(\)]+$',
            message='Enter a valid phone number'
        )]
    )
    
    class Meta:
        ordering = ['company', 'last_name', 'first_name']
        unique_together = [
            ['company', 'customer_id'],  # Customer ID unique per company
            ['company', 'email'],        # Email unique per company
            ['company', 'national_id'],  # National ID unique per company
        ]
        indexes = [
            models.Index(fields=['company', 'customer_id']),
            models.Index(fields=['company', 'email']),
            models.Index(fields=['company', 'national_id']),
            models.Index(fields=['company', 'last_name', 'first_name']),
            models.Index(fields=['company', 'customer_type', 'is_active']),
            models.Index(fields=['company', 'risk_rating']),
        ]
    
    def __str__(self):
        if self.customer_type == 'business':
            return f"{self.business_name} ({self.customer_id}) - {self.company.name}"
        return f"{self.first_name} {self.last_name} ({self.customer_id}) - {self.company.name}"
    
    @property
    def full_name(self):
        if self.customer_type == 'business':
            return self.business_name
        return f"{self.first_name} {self.last_name}"
    
    @property
    def total_monthly_income(self):
        """Calculate total monthly income including other sources"""
        income = self.monthly_income or Decimal('0.00')
        other = self.other_income or Decimal('0.00')
        return income + other
    
    @property
    def debt_to_income_ratio(self):
        """Calculate debt-to-income ratio as percentage"""
        if not self.total_monthly_income or self.total_monthly_income == 0:
            return None
        return (self.existing_debt_payments / self.total_monthly_income) * 100
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            # Generate unique customer ID per company
            from django.utils import timezone
            import random
            year = timezone.now().year
            random_num = random.randint(10000, 99999)
            self.customer_id = f"CU{year}{random_num}"
            # Ensure uniqueness within company
            while Customer.objects.filter(
                company=self.company, 
                customer_id=self.customer_id
            ).exists():
                random_num = random.randint(10000, 99999)
                self.customer_id = f"CU{year}{random_num}"
        super().save(*args, **kwargs)


class CustomerDocument(BaseLoanModel):
    """Document storage for customer files - Company separated"""
    
    DOCUMENT_TYPE = [
        ('id_document', 'ID Document'),
        ('proof_of_income', 'Proof of Income'),
        ('bank_statement', 'Bank Statement'),
        ('employment_letter', 'Employment Letter'),
        ('tax_return', 'Tax Return'),
        ('business_license', 'Business License'),
        ('financial_statement', 'Financial Statement'),
        ('collateral_document', 'Collateral Document'),
        ('other', 'Other'),
    ]
    
    DOCUMENT_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE)
    document_name = models.CharField(max_length=200)
    file_path = models.FileField(upload_to='customer_documents/%Y/%m/')
    file_size = models.IntegerField(help_text="File size in bytes")
    
    # Document Details
    description = models.TextField(blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    
    # Review Status
    status = models.CharField(max_length=20, choices=DOCUMENT_STATUS, default='pending')
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_customer_documents'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company', '-created_at']
        indexes = [
            models.Index(fields=['company', 'customer', 'document_type']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'expiry_date']),
            models.Index(fields=['company', 'document_type']),
        ]
    
    def __str__(self):
        return f"{self.customer} - {self.document_name} ({self.company.name})"
    
    @property
    def is_expired(self):
        """Check if document has expired"""
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
