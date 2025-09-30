from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from .base_models import BaseLoanModel

class LoanProduct(BaseLoanModel):
    """Defines loan product types and their characteristics - Company separated"""
    
    CATEGORY_CHOICES = [
        ('personal', 'Personal Loan'),
        ('business', 'Business Loan'),
        ('auto', 'Auto Loan'),
        ('mortgage', 'Mortgage'),
        ('education', 'Education Loan'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=100, help_text="Product name (e.g., 'Personal Loan - Premium')")
    code = models.CharField(max_length=20, help_text="Unique product code (e.g., 'PL001')")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    
    # Loan Limits
    min_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))],
        help_text="Minimum loan amount"
    )
    max_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))],
        help_text="Maximum loan amount"
    )
    
    # Term Limits
    min_term_months = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        help_text="Minimum loan term in months"
    )
    max_term_months = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        help_text="Maximum loan term in months"
    )
    
    # Interest Rate
    default_interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('99.99'))],
        help_text="Default annual interest rate (percentage)"
    )
    
    # Product Features
    allows_prepayment = models.BooleanField(default=True)
    prepayment_penalty_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('10.00'))],
        help_text="Prepayment penalty as percentage of outstanding balance"
    )
    
    # Late Payment Configuration
    grace_period_days = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        help_text="Grace period before late fees apply"
    )
    late_fee_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('25.00'),
        help_text="Flat late fee amount"
    )
    late_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('25.00'))],
        help_text="Late fee as percentage of overdue amount"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['company', 'category', 'name']
        unique_together = [['company', 'code']]  # Code unique per company
        indexes = [
            models.Index(fields=['company', 'category', 'is_active']),
            models.Index(fields=['company', 'code']),
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.company.name})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.min_amount > self.max_amount:
            raise ValidationError("Minimum amount cannot be greater than maximum amount")
        if self.min_term_months > self.max_term_months:
            raise ValidationError("Minimum term cannot be greater than maximum term")


class LoanApplication(BaseLoanModel):
    """Main loan application record - Company separated"""
    
    APPLICATION_STATUS = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    REPAYMENT_METHOD = [
        ('equal_principal', 'Equal Principal'),
        ('equal_payment', 'Equal Payment (Annuity)'),
        ('custom', 'Custom Schedule'),
        ('interest_only', 'Interest Only + Balloon'),
    ]
    
    PAYMENT_FREQUENCY = [
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    # Identifiers
    application_id = models.CharField(max_length=20, editable=False)
    customer = models.ForeignKey('loans_customers.Customer', on_delete=models.PROTECT)
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT)
    
    # Loan Details
    requested_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))]
    )
    approved_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('100.00'))]
    )
    term_months = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(600)]
    )
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('99.99'))]
    )
    
    # Repayment Configuration
    repayment_method = models.CharField(max_length=20, choices=REPAYMENT_METHOD, default='equal_payment')
    payment_frequency = models.CharField(max_length=20, choices=PAYMENT_FREQUENCY, default='monthly')
    
    # Custom Schedule Settings
    grace_period_months = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(12)])
    balloon_payment_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Final balloon payment amount"
    )
    custom_schedule_config = models.JSONField(
        null=True, 
        blank=True,
        help_text="JSON configuration for custom payment schedules"
    )
    
    # Important Dates
    application_date = models.DateField(auto_now_add=True)
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    first_payment_date = models.DateField(null=True, blank=True)
    
    # Status & Processing
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS, default='draft')
    assigned_officer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_loan_applications'
    )
    
    # Documentation
    purpose = models.TextField(help_text="Purpose of the loan")
    collateral_description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company', '-application_date', '-created_at']
        unique_together = [['company', 'application_id']]  # Application ID unique per company
        indexes = [
            models.Index(fields=['company', 'customer', 'status']),
            models.Index(fields=['company', 'application_id']),
            models.Index(fields=['company', 'status', 'application_date']),
            models.Index(fields=['company', 'assigned_officer']),
        ]
    
    def __str__(self):
        return f"Application {self.application_id} - {self.customer} ({self.company.name})"
    
    def save(self, *args, **kwargs):
        if not self.application_id:
            # Generate unique application ID per company
            from django.utils import timezone
            import random
            year = timezone.now().year
            random_num = random.randint(1000, 9999)
            self.application_id = f"APP{year}{random_num}"
            # Ensure uniqueness within company
            while LoanApplication.objects.filter(
                company=self.company, 
                application_id=self.application_id
            ).exists():
                random_num = random.randint(1000, 9999)
                self.application_id = f"APP{year}{random_num}"
        super().save(*args, **kwargs)
    
    def get_approval_progress(self):
        """Calculate approval progress for payments with intelligent caching"""
        # Try to get from cache first
        try:
            from core.cache_system import loan_cache
            cached_progress = loan_cache.get_cached_approval_progress(self.id)
            if cached_progress:
                return cached_progress
        except ImportError:
            pass  # Cache system not available
        
        if self.status != 'approved':
            result = {
                'total_payments': 0,
                'approved_payments': 0,
                'percentage': 0,
                'status': 'not_started',
                'status_display': 'Not Started'
            }
            
            # Cache the result
            try:
                from core.cache_system import loan_cache
                loan_cache.cache_approval_progress(self.id, result)
            except ImportError:
                pass
            
            return result
        
        try:
            # Get the associated loan
            loan = self.loan
            
            # Optimized: Get payments with prefetched related data
            from loans_payments.models import Payment
            from django.db.models import Exists, OuterRef
            from journal.models import Journal
            
            # Single query to get payments with approval status
            payments_with_approval = Payment.objects.filter(
                loan=loan
            ).annotate(
                is_approved=Exists(
                    Journal.objects.filter(
                        company=self.company,
                        reference=models.Concat(
                            models.Value('SPLIT-'), 
                            OuterRef('payment_id')
                        )
                    )
                )
            )
            
            total_payments = payments_with_approval.count()
            
            if total_payments == 0:
                result = {
                    'total_payments': 0,
                    'approved_payments': 0,
                    'percentage': 0,
                    'status': 'not_started',
                    'status_display': 'No Payments'
                }
            else:
                # Count approved payments in single query
                approved_payments = payments_with_approval.filter(is_approved=True).count()
                
                # Calculate percentage
                percentage = round((approved_payments / total_payments) * 100)
                
                # Determine status
                if approved_payments == 0:
                    status = 'not_started'
                    status_display = 'Not Started'
                elif approved_payments == total_payments:
                    status = 'completed'
                    status_display = 'All Approved'
                else:
                    status = 'partial'
                    status_display = 'Partially Approved'
                
                result = {
                    'total_payments': total_payments,
                    'approved_payments': approved_payments,
                    'percentage': percentage,
                    'status': status,
                    'status_display': status_display
                }
            
            # Cache the result for 10 minutes
            try:
                from core.cache_system import loan_cache
                loan_cache.cache_approval_progress(self.id, result)
            except ImportError:
                pass
            
            return result
            
        except Exception:
            # If no loan exists yet (approved but not disbursed)
            result = {
                'total_payments': 0,
                'approved_payments': 0,
                'percentage': 0,
                'status': 'pending_disbursement',
                'status_display': 'Pending Disbursement'
            }
            
            # Cache the result
            try:
                from core.cache_system import loan_cache
                loan_cache.cache_approval_progress(self.id, result)
            except ImportError:
                pass
                
            return result
    
    def get_progress_badge_class(self):
        """Get CSS class for progress badge"""
        progress = self.get_approval_progress()
        status = progress['status']
        
        badge_classes = {
            'not_started': 'badge-secondary',
            'pending_disbursement': 'badge-info',
            'partial': 'badge-warning',
            'completed': 'badge-success'
        }
        
        return badge_classes.get(status, 'badge-secondary')


class Loan(BaseLoanModel):
    """Active loan record (created after approval and disbursement) - Company separated"""
    
    LOAN_STATUS = [
        ('active', 'Active'),
        ('paid_off', 'Paid Off'),
        ('defaulted', 'Defaulted'),
        ('written_off', 'Written Off'),
        ('restructured', 'Restructured'),
        ('suspended', 'Suspended'),
    ]
    
    # Identifiers
    loan_number = models.CharField(max_length=20, editable=False)
    application = models.OneToOneField(LoanApplication, on_delete=models.PROTECT)
    customer = models.ForeignKey('loans_customers.Customer', on_delete=models.PROTECT)
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT)
    
    # Loan Terms (copied from approved application)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.IntegerField()
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Important Dates
    disbursement_date = models.DateField()
    first_payment_date = models.DateField()
    maturity_date = models.DateField()
    
    # Current Status
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='active')
    payments_made = models.IntegerField(default=0)
    payments_remaining = models.IntegerField()
    last_payment_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField()
    
    # Financial Totals
    total_interest_charged = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_fees_charged = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_payments_received = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Risk & Performance Metrics
    days_overdue = models.IntegerField(default=0)
    overdue_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    highest_days_overdue = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['company', '-disbursement_date', '-created_at']
        unique_together = [['company', 'loan_number']]  # Loan number unique per company
        indexes = [
            models.Index(fields=['company', 'customer', 'status']),
            models.Index(fields=['company', 'loan_number']),
            models.Index(fields=['company', 'status', 'next_payment_date']),
            models.Index(fields=['company', 'days_overdue']),
            models.Index(fields=['company', 'application']),
        ]
    
    def __str__(self):
        return f"Loan {self.loan_number} - {self.customer} ({self.company.name})"
    
    def save(self, *args, **kwargs):
        if not self.loan_number:
            # Generate unique loan number per company
            from django.utils import timezone
            import random
            year = timezone.now().year
            random_num = random.randint(100000, 999999)
            self.loan_number = f"LN{year}{random_num}"
            # Ensure uniqueness within company
            while Loan.objects.filter(
                company=self.company, 
                loan_number=self.loan_number
            ).exists():
                random_num = random.randint(100000, 999999)
                self.loan_number = f"LN{year}{random_num}"
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if loan has overdue payments"""
        from django.utils import timezone
        return self.next_payment_date < timezone.now().date() and self.status == 'active'
    
    @property
    def payment_performance_ratio(self):
        """Calculate payment performance as percentage"""
        if self.term_months == 0:
            return 0
        return (self.payments_made / self.term_months) * 100
