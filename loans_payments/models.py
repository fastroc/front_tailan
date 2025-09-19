from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from loans_core.base_models import BaseLoanModel

class Payment(BaseLoanModel):
    """Record of actual payments received - Company separated"""
    
    PAYMENT_METHOD = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('ach', 'ACH/Direct Debit'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('money_order', 'Money Order'),
        ('wire_transfer', 'Wire Transfer'),
        ('online', 'Online Payment'),
        ('mobile_app', 'Mobile App'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_TYPE = [
        ('regular', 'Regular Payment'),
        ('prepayment', 'Prepayment'),
        ('late_payment', 'Late Payment'),
        ('payoff', 'Loan Payoff'),
        ('fee_payment', 'Fee Payment'),
        ('partial', 'Partial Payment'),
    ]
    
    # Identifiers
    payment_id = models.CharField(max_length=20, editable=False)
    transaction_id = models.CharField(max_length=100, blank=True, help_text="External transaction ID from payment processor")
    
    # Relationships
    loan = models.ForeignKey('loans_core.Loan', on_delete=models.PROTECT, related_name='payments')
    customer = models.ForeignKey('loans_customers.Customer', on_delete=models.PROTECT, related_name='payments')
    scheduled_payment = models.ForeignKey(
        'loans_schedule.ScheduledPayment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Link to scheduled payment if this is for a specific scheduled payment"
    )
    
    # Payment Details
    payment_date = models.DateField()
    payment_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE, default='regular')
    
    # Payment Processing
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    processed_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='processed_loan_payments'
    )
    
    # Payment Source Details
    reference_number = models.CharField(max_length=100, blank=True, help_text="Check number, confirmation number, etc.")
    bank_name = models.CharField(max_length=100, blank=True)
    account_last_four = models.CharField(max_length=4, blank=True, help_text="Last 4 digits of account")
    
    # Fees and Charges
    processing_fee = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    late_fee_included = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Net Amounts (after fees)
    net_payment_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Payment amount minus fees"
    )
    
    # Notes and Comments
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True, help_text="Internal staff notes")
    
    # Failure/Cancellation Details
    failure_reason = models.TextField(blank=True)
    cancelled_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cancelled_loan_payments'
    )
    cancelled_date = models.DateTimeField(null=True, blank=True)
    
    # Refund Information
    refund_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    refund_date = models.DateField(null=True, blank=True)
    refund_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company', '-payment_date', '-created_at']
        unique_together = [['company', 'payment_id']]  # Payment ID unique per company
        indexes = [
            models.Index(fields=['company', 'loan', 'payment_date']),
            models.Index(fields=['company', 'customer', 'payment_date']),
            models.Index(fields=['company', 'payment_id']),
            models.Index(fields=['company', 'status', 'payment_date']),
            models.Index(fields=['company', 'transaction_id']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - ${self.payment_amount} for {self.loan.loan_number} ({self.company.name})"
    
    def save(self, *args, **kwargs):
        if not self.payment_id:
            # Generate unique payment ID per company
            from django.utils import timezone
            import random
            year = timezone.now().year
            random_num = random.randint(100000, 999999)
            self.payment_id = f"PAY{year}{random_num}"
            # Ensure uniqueness within company
            while Payment.objects.filter(
                company=self.company, 
                payment_id=self.payment_id
            ).exists():
                random_num = random.randint(100000, 999999)
                self.payment_id = f"PAY{year}{random_num}"
        
        # Calculate net payment amount
        if not self.net_payment_amount:
            self.net_payment_amount = self.payment_amount - self.processing_fee
        
        super().save(*args, **kwargs)
    
    @property
    def effective_payment_amount(self):
        """Calculate effective payment amount after refunds"""
        return self.payment_amount - self.refund_amount
    
    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == 'completed'


class PaymentAllocation(BaseLoanModel):
    """Detailed breakdown of how payment amounts are allocated - Company separated"""
    
    ALLOCATION_TYPE = [
        ('principal', 'Principal'),
        ('interest', 'Interest'),
        ('late_fee', 'Late Fee'),
        ('processing_fee', 'Processing Fee'),
        ('prepayment_penalty', 'Prepayment Penalty'),
        ('other_fee', 'Other Fee'),
    ]
    
    # Relationships
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    loan = models.ForeignKey('loans_core.Loan', on_delete=models.PROTECT)
    scheduled_payment = models.ForeignKey(
        'loans_schedule.ScheduledPayment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Allocation Details
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPE)
    allocation_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    allocation_order = models.IntegerField(help_text="Order in which this allocation was applied")
    
    # Balance Impact
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Allocation Context
    description = models.CharField(max_length=200, help_text="Description of what this allocation covers")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company', 'payment', 'allocation_order']
        indexes = [
            models.Index(fields=['company', 'payment', 'allocation_order']),
            models.Index(fields=['company', 'loan', 'allocation_type']),
            models.Index(fields=['company', 'scheduled_payment']),
        ]
    
    def __str__(self):
        return f"{self.allocation_type.title()}: ${self.allocation_amount} for {self.payment.payment_id} ({self.company.name})"


class PaymentHistory(BaseLoanModel):
    """Audit trail for payment changes and status updates - Company separated"""
    
    ACTION_TYPE = [
        ('created', 'Payment Created'),
        ('processed', 'Payment Processed'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
        ('cancelled', 'Payment Cancelled'),
        ('refunded', 'Payment Refunded'),
        ('allocated', 'Payment Allocated'),
        ('updated', 'Payment Updated'),
    ]
    
    # Relationships
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    
    # History Details
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE)
    action_date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Change Details
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    old_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Additional Context
    description = models.TextField(help_text="Description of the change or action")
    system_notes = models.TextField(blank=True, help_text="System-generated notes")
    
    class Meta:
        ordering = ['company', '-action_date']
        indexes = [
            models.Index(fields=['company', 'payment', 'action_date']),
            models.Index(fields=['company', 'action_type', 'action_date']),
        ]
    
    def __str__(self):
        return f"{self.action_type} - {self.payment.payment_id} at {self.action_date} ({self.company.name})"


class AutoPayment(BaseLoanModel):
    """Automatic payment configuration for loans - Company separated"""
    
    AUTOPAY_STATUS = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed - Needs Attention'),
    ]
    
    FREQUENCY = [
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    # Relationships
    loan = models.OneToOneField('loans_core.Loan', on_delete=models.CASCADE, related_name='autopay')
    customer = models.ForeignKey('loans_customers.Customer', on_delete=models.PROTECT)
    
    # AutoPay Configuration
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=AUTOPAY_STATUS, default='active')
    frequency = models.CharField(max_length=20, choices=FREQUENCY, default='monthly')
    
    # Payment Details
    payment_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Fixed payment amount (leave blank for scheduled amount)"
    )
    payment_day = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Day of month for payment (1-31)"
    )
    
    # Banking Information
    bank_account_name = models.CharField(max_length=100)
    bank_routing_number = models.CharField(max_length=20)
    bank_account_number_encrypted = models.CharField(max_length=200, help_text="Encrypted account number")
    account_type = models.CharField(
        max_length=20, 
        choices=[('checking', 'Checking'), ('savings', 'Savings')]
    )
    
    # Failure Handling
    max_retry_attempts = models.IntegerField(default=3)
    current_failures = models.IntegerField(default=0)
    last_failure_date = models.DateField(null=True, blank=True)
    last_failure_reason = models.TextField(blank=True)
    
    # Next Payment Info
    next_payment_date = models.DateField()
    next_payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Agreement Details
    agreement_date = models.DateField()
    agreement_ip_address = models.GenericIPAddressField(null=True, blank=True)
    terms_accepted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['company', 'loan']
        indexes = [
            models.Index(fields=['company', 'loan', 'status']),
            models.Index(fields=['company', 'next_payment_date', 'is_active']),
            models.Index(fields=['company', 'status']),
        ]
    
    def __str__(self):
        return f"AutoPay for {self.loan.loan_number} - ${self.payment_amount} ({self.company.name})"
    
    def calculate_next_payment_date(self):
        """Calculate next payment date based on frequency"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        today = date.today()
        
        if self.frequency == 'monthly':
            next_date = today.replace(day=self.payment_day)
            if next_date <= today:
                next_date = next_date + relativedelta(months=1)
        elif self.frequency == 'bi_monthly':
            next_date = today.replace(day=self.payment_day)
            if next_date <= today:
                next_date = next_date + relativedelta(months=2)
        elif self.frequency == 'quarterly':
            next_date = today.replace(day=self.payment_day)
            if next_date <= today:
                next_date = next_date + relativedelta(months=3)
        
        return next_date
    
    def increment_failure_count(self, reason):
        """Increment failure count and update status if needed"""
        from django.utils import timezone
        
        self.current_failures += 1
        self.last_failure_date = timezone.now().date()
        self.last_failure_reason = reason
        
        if self.current_failures >= self.max_retry_attempts:
            self.status = 'failed'
            self.is_active = False
        
        self.save()
    
    def reset_failure_count(self):
        """Reset failure count after successful payment"""
        self.current_failures = 0
        self.last_failure_date = None
        self.last_failure_reason = ''
        if self.status == 'failed':
            self.status = 'active'
        self.save()
