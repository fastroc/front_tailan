from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from loans_core.base_models import BaseLoanModel

class PaymentSchedule(BaseLoanModel):
    """Master payment schedule for a loan - Company separated"""
    
    SCHEDULE_TYPE = [
        ('equal_principal', 'Equal Principal'),
        ('equal_payment', 'Equal Payment (Annuity)'),
        ('custom', 'Custom Schedule'),
        ('interest_only', 'Interest Only + Balloon'),
    ]
    
    FREQUENCY = [
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('restructured', 'Restructured'),
        ('suspended', 'Suspended'),
    ]
    
    # Identifiers
    loan = models.OneToOneField('loans_core.Loan', on_delete=models.CASCADE, related_name='payment_schedule')
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE)
    payment_frequency = models.CharField(max_length=20, choices=FREQUENCY)
    
    # Schedule Parameters
    total_payments = models.IntegerField()
    payments_completed = models.IntegerField(default=0)
    
    # Financial Totals
    total_principal = models.DecimalField(max_digits=12, decimal_places=2)
    total_interest = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Special Features
    grace_period_months = models.IntegerField(default=0)
    balloon_payment_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    
    class Meta:
        ordering = ['company', 'loan']
        indexes = [
            models.Index(fields=['company', 'loan', 'status']),
            models.Index(fields=['company', 'schedule_type']),
            models.Index(fields=['company', 'status']),
        ]
    
    def __str__(self):
        return f"Payment Schedule for {self.loan.loan_number} ({self.company.name})"
    
    @property
    def completion_percentage(self):
        """Calculate schedule completion percentage"""
        if self.total_payments == 0:
            return 0
        return (self.payments_completed / self.total_payments) * 100
    
    @property
    def remaining_payments(self):
        """Calculate remaining payments"""
        return self.total_payments - self.payments_completed


class ScheduledPayment(BaseLoanModel):
    """Individual scheduled payment within a payment schedule - Company separated"""
    
    PAYMENT_TYPE = [
        ('regular', 'Regular Payment'),
        ('grace', 'Grace Period'),
        ('balloon', 'Balloon Payment'),
        ('final', 'Final Payment'),
    ]
    
    STATUS = [
        ('scheduled', 'Scheduled'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partial', 'Partially Paid'),
        ('skipped', 'Skipped'),
        ('waived', 'Waived'),
    ]
    
    # Relationships
    payment_schedule = models.ForeignKey(PaymentSchedule, on_delete=models.CASCADE, related_name='scheduled_payments')
    loan = models.ForeignKey('loans_core.Loan', on_delete=models.CASCADE, related_name='scheduled_payments')
    
    # Payment Details
    payment_number = models.IntegerField(help_text="Sequential payment number (1, 2, 3, ...)")
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE, default='regular')
    due_date = models.DateField()
    
    # Payment Breakdown
    principal_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    interest_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Running Balances
    beginning_balance = models.DecimalField(max_digits=12, decimal_places=2)
    ending_balance = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment Status
    status = models.CharField(max_length=20, choices=STATUS, default='scheduled')
    amount_paid = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    payment_date = models.DateField(null=True, blank=True)
    
    # Late Payment Tracking
    days_overdue = models.IntegerField(default=0)
    late_fees_assessed = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Custom Payment Features
    is_custom_amount = models.BooleanField(default=False, help_text="True if this payment has a custom amount")
    original_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Original calculated amount if custom amount is used"
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company', 'payment_number']
        unique_together = [['company', 'payment_schedule', 'payment_number']]
        indexes = [
            models.Index(fields=['company', 'loan', 'due_date']),
            models.Index(fields=['company', 'status', 'due_date']),
            models.Index(fields=['company', 'payment_schedule', 'payment_number']),
            models.Index(fields=['company', 'due_date']),
        ]
    
    def __str__(self):
        return f"Payment #{self.payment_number} for {self.loan.loan_number} - Due: {self.due_date} ({self.company.name})"
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        if self.status in ['paid', 'waived', 'skipped']:
            return False
        from django.utils import timezone
        return self.due_date < timezone.now().date()
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        return self.total_amount - self.amount_paid
    
    @property
    def is_fully_paid(self):
        """Check if payment is fully paid"""
        return self.amount_paid >= self.total_amount
    
    def update_overdue_status(self):
        """Update overdue status and days overdue"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.status in ['paid', 'waived', 'skipped']:
            self.days_overdue = 0
            return
        
        if self.due_date < today:
            self.days_overdue = (today - self.due_date).days
            if self.amount_paid < self.total_amount:
                self.status = 'overdue' if self.amount_paid == 0 else 'partial'
        else:
            self.days_overdue = 0
            if self.status == 'overdue' and self.amount_paid == 0:
                self.status = 'scheduled'


class CustomPaymentPreset(BaseLoanModel):
    """Predefined payment schedule templates for quick setup - Company separated"""
    
    PRESET_TYPE = [
        ('equal_payment', 'Equal Payment'),
        ('equal_principal', 'Equal Principal'),
        ('custom', 'Custom Schedule'),
        ('interest_only', 'Interest Only + Balloon'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=100, help_text="Preset name (e.g., 'Salary-Based Monthly')")
    description = models.TextField(help_text="Description of when to use this preset")
    preset_type = models.CharField(max_length=20, choices=PRESET_TYPE)
    
    # Default Configuration
    default_frequency = models.CharField(max_length=20, choices=PaymentSchedule.FREQUENCY, default='monthly')
    grace_period_months = models.IntegerField(default=0)
    
    # Custom Schedule Configuration
    payment_pattern = models.JSONField(
        null=True, 
        blank=True,
        help_text="JSON array defining custom payment amounts or percentages"
    )
    
    # Special Features
    has_balloon_payment = models.BooleanField(default=False)
    balloon_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Balloon payment as percentage of principal"
    )
    
    # Usage Statistics
    usage_count = models.IntegerField(default=0, help_text="How many times this preset has been used")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['company', '-usage_count', 'name']
        unique_together = [['company', 'name']]  # Preset name unique per company
        indexes = [
            models.Index(fields=['company', 'preset_type', 'is_active']),
            models.Index(fields=['company', 'usage_count']),
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.preset_type}) - {self.company.name}"
    
    def increment_usage(self):
        """Increment usage counter when preset is used"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class PaymentDateRule(BaseLoanModel):
    """Rules for calculating payment due dates - Company separated"""
    
    RULE_TYPE = [
        ('monthly_same_day', 'Same Day Each Month'),
        ('monthly_last_day', 'Last Day of Month'),
        ('weekly_same_weekday', 'Same Weekday Each Week'),
        ('bi_weekly_from_start', 'Every 2 Weeks from Start Date'),
        ('custom_dates', 'Custom Date List'),
    ]
    
    # Rule Configuration
    rule_name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE)
    
    # Parameters for different rule types
    day_of_month = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="For monthly rules: day of month (1-31)"
    )
    weekday = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="For weekly rules: weekday (0=Monday, 6=Sunday)"
    )
    custom_dates = models.JSONField(
        null=True, 
        blank=True,
        help_text="For custom rules: array of specific dates"
    )
    
    # Business Rules
    skip_weekends = models.BooleanField(default=True, help_text="Move weekend dates to next business day")
    skip_holidays = models.BooleanField(default=False, help_text="Move holiday dates to next business day")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['company', 'rule_name']
        unique_together = [['company', 'rule_name']]  # Rule name unique per company
        indexes = [
            models.Index(fields=['company', 'rule_type', 'is_active']),
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.rule_name} ({self.company.name})"
    
    def calculate_due_dates(self, start_date, num_payments):
        """Calculate due dates based on the rule"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        due_dates = []
        current_date = start_date
        
        for i in range(num_payments):
            if self.rule_type == 'monthly_same_day':
                if i == 0:
                    due_date = current_date
                else:
                    due_date = current_date + relativedelta(months=i)
                    
            elif self.rule_type == 'weekly_same_weekday':
                due_date = current_date + timedelta(weeks=i)
                
            elif self.rule_type == 'bi_weekly_from_start':
                due_date = current_date + timedelta(weeks=i*2)
                
            # Apply business day adjustments
            if self.skip_weekends:
                while due_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    due_date += timedelta(days=1)
            
            due_dates.append(due_date)
        
        return due_dates
