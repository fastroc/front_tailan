from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from loans_core.base_models import BaseLoanModel


class PaymentManager(models.Manager):
    """Enhanced Payment Manager with three-tier system queries"""
    
    def by_source(self, source):
        """Filter payments by data source"""
        return self.filter(data_source=source)
    
    def manual_entries(self):
        """Get manually entered payments"""
        return self.filter(data_source='manual')
    
    def bulk_uploads(self):
        """Get bulk uploaded payments"""
        return self.filter(data_source='bulk_upload')
    
    def reconciliation_payments(self):
        """Get bank reconciliation payments"""
        return self.filter(data_source='reconciliation')
    
    def bank_verified(self):
        """Get bank-verified payments"""
        return self.filter(is_bank_verified=True)
    
    def pending_reconciliation(self):
        """Get payments awaiting bank reconciliation"""
        return self.filter(reconciliation_status='pending')
    
    def final_audited(self):
        """Get audit-locked payments"""
        return self.filter(reconciliation_status='final')
    
    def reconciliation_summary(self, company, date_range=None):
        """Get reconciliation status summary"""
        qs = self.filter(company=company)
        if date_range:
            qs = qs.filter(payment_date__range=date_range)
        
        return qs.aggregate(
            total_payments=models.Count('id'),
            manual_count=models.Count('id', filter=models.Q(data_source='manual')),
            bulk_count=models.Count('id', filter=models.Q(data_source='bulk_upload')),
            reconciled_count=models.Count('id', filter=models.Q(data_source='reconciliation')),
            bank_verified_count=models.Count('id', filter=models.Q(is_bank_verified=True)),
            pending_reconciliation=models.Count('id', filter=models.Q(reconciliation_status='pending')),
            total_amount=models.Sum('payment_amount'),
            bank_verified_amount=models.Sum('payment_amount', filter=models.Q(is_bank_verified=True))
        )


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
    
    # === THREE-TIER PAYMENT SYSTEM FIELDS ===
    
    # Data Source Identification
    data_source = models.CharField(
        max_length=20, 
        choices=[
            ('manual', 'Manual Entry'),
            ('bulk_upload', 'Bulk Upload'),
            ('reconciliation', 'Bank Reconciliation'),
            ('api', 'API Integration'),
        ], 
        default='manual', 
        help_text="Source of payment data entry",
        db_index=True
    )
    
    # Reconciliation Status Tracking
    reconciliation_status = models.CharField(
        max_length=20, 
        choices=[
            ('not_required', 'Not Required'),        # Manual/cash payments
            ('pending', 'Awaiting Reconciliation'),  # Needs bank verification
            ('matched', 'Bank Reconciled'),          # Matched with bank transaction
            ('unmatched', 'Reconciliation Failed'),  # Cannot match with bank
            ('final', 'Final/Audited'),             # Locked for audit compliance
        ], 
        default='not_required',
        help_text="Status of bank reconciliation process",
        db_index=True
    )
    
    # Bank Transaction Links (for reconciliation payments only)
    bank_transaction = models.ForeignKey(
        'bank_accounts.BankTransaction', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Linked bank transaction (reconciliation source only)",
        related_name='loan_payments'
    )
    
    transaction_match = models.ForeignKey(
        'reconciliation.TransactionMatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True, 
        help_text="Reconciliation match record reference",
        related_name='loan_payments'
    )
    
    # Bank Verification Audit Fields
    is_bank_verified = models.BooleanField(
        default=False,
        help_text="True if payment verified against bank statement",
        db_index=True
    )
    
    bank_verification_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp when payment was bank-verified"
    )
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_loan_payments',
        help_text="User who verified payment against bank statement"
    )
    
    # Reconciliation Process Notes
    reconciliation_notes = models.TextField(
        blank=True,
        help_text="Internal notes from bank reconciliation process"
    )
    
    # === CUSTOM MANAGER ===
    objects = PaymentManager()
    
    class Meta:
        ordering = ['company', '-payment_date', '-created_at']
        unique_together = [['company', 'payment_id']]  # Payment ID unique per company
        indexes = [
            models.Index(fields=['company', 'loan', 'payment_date']),
            models.Index(fields=['company', 'customer', 'payment_date']),
            models.Index(fields=['company', 'payment_id']),
            models.Index(fields=['company', 'status', 'payment_date']),
            models.Index(fields=['company', 'transaction_id']),
            # === THREE-TIER PAYMENT SYSTEM INDEXES ===
            models.Index(fields=['company', 'data_source', 'payment_date']),
            models.Index(fields=['company', 'reconciliation_status']),
            models.Index(fields=['company', 'is_bank_verified', 'payment_date']),
            models.Index(fields=['bank_transaction']),  # For reconciliation lookups
            models.Index(fields=['transaction_match']),  # For reconciliation lookups
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
    
    # === THREE-TIER PAYMENT SYSTEM PROPERTIES ===
    
    @property
    def is_reconciliation_payment(self):
        """Check if payment originated from bank reconciliation"""
        return self.data_source == 'reconciliation'
    
    @property
    def is_bank_sourced(self):
        """Check if payment has verified bank transaction source"""
        return bool(self.bank_transaction and self.is_bank_verified)
    
    @property
    def reconciliation_priority(self):
        """Return reconciliation priority level (lower = higher priority)"""
        priority_map = {
            'reconciliation': 1,  # Highest priority - bank verified
            'bulk_upload': 2,     # Medium priority - systematic
            'manual': 3,          # Lower priority - manual entry
            'api': 2,            # Medium priority - systematic
        }
        return priority_map.get(self.data_source, 99)
    
    @property
    def needs_reconciliation(self):
        """Check if payment needs bank reconciliation"""
        return self.reconciliation_status == 'pending'
    
    @property
    def is_final_audited(self):
        """Check if payment is locked for audit"""
        return self.reconciliation_status == 'final'
    
    @property
    def reconciliation_match_status(self):
        """Check if this payment has a matching counterpart from different data source"""
        from decimal import Decimal
        from datetime import timedelta
        
        # If this is a reconciliation payment, look for manual entries
        if self.data_source == 'reconciliation':
            matching_manual = Payment.objects.filter(
                loan=self.loan,
                data_source='manual',
                payment_date__range=[
                    self.payment_date - timedelta(days=3), 
                    self.payment_date + timedelta(days=3)
                ],
                payment_amount__range=[
                    self.payment_amount - Decimal('5.00'),
                    self.payment_amount + Decimal('5.00')
                ]
            ).first()
            
            if matching_manual:
                amount_diff = abs(self.payment_amount - matching_manual.payment_amount)
                date_diff = abs((self.payment_date - matching_manual.payment_date).days)
                
                if amount_diff == 0 and date_diff == 0:
                    return {'status': 'perfect_match', 'match': matching_manual}
                elif amount_diff <= 5 and date_diff <= 1:
                    return {'status': 'close_match', 'match': matching_manual, 'amount_diff': amount_diff, 'date_diff': date_diff}
                else:
                    return {'status': 'loose_match', 'match': matching_manual, 'amount_diff': amount_diff, 'date_diff': date_diff}
            else:
                return {'status': 'no_match', 'match': None}
        
        # If this is a manual payment, look for reconciliation entries
        elif self.data_source == 'manual':
            matching_recon = Payment.objects.filter(
                loan=self.loan,
                data_source='reconciliation',
                payment_date__range=[
                    self.payment_date - timedelta(days=3), 
                    self.payment_date + timedelta(days=3)
                ],
                payment_amount__range=[
                    self.payment_amount - Decimal('5.00'),
                    self.payment_amount + Decimal('5.00')
                ]
            ).first()
            
            if matching_recon:
                amount_diff = abs(self.payment_amount - matching_recon.payment_amount)
                date_diff = abs((self.payment_date - matching_recon.payment_date).days)
                
                if amount_diff == 0 and date_diff == 0:
                    return {'status': 'perfect_match', 'match': matching_recon}
                elif amount_diff <= 5 and date_diff <= 1:
                    return {'status': 'close_match', 'match': matching_recon, 'amount_diff': amount_diff, 'date_diff': date_diff}
                else:
                    return {'status': 'loose_match', 'match': matching_recon, 'amount_diff': amount_diff, 'date_diff': date_diff}
            else:
                return {'status': 'pending_reconciliation', 'match': None}
        
        # For bulk_upload or other sources
        else:
            return {'status': 'not_applicable', 'match': None}
    
    def mark_bank_verified(self, verified_by_user, bank_transaction=None, notes=''):
        """Mark payment as bank verified"""
        from django.utils import timezone
        self.is_bank_verified = True
        self.bank_verification_date = timezone.now()
        self.verified_by = verified_by_user
        self.reconciliation_status = 'matched'
        if bank_transaction:
            self.bank_transaction = bank_transaction
        if notes:
            self.reconciliation_notes = notes
        self.save()
    
    def finalize_for_audit(self, user):
        """Lock payment for audit compliance"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.reconciliation_status != 'matched':
            raise ValidationError("Payment must be bank reconciled before finalizing")
        self.reconciliation_status = 'final'
        self.reconciliation_notes += f"\n[{timezone.now()}] Finalized for audit by {user.username}"
        self.save()


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


class PaymentPolicy(BaseLoanModel):
    """Configurable payment processing policies - Company separated"""
    
    ALLOCATION_METHOD = [
        ('interest_first', 'Interest First (Industry Standard)'),
        ('principal_first', 'Principal First'),
        ('proportional', 'Proportional Interest/Principal'),
        ('customer_directed', 'Customer Directed'),
    ]
    
    WEEKEND_POSTING = [
        ('same_day', 'Same Day'),
        ('next_business_day', 'Next Business Day'),
        ('previous_business_day', 'Previous Business Day'),
    ]
    
    # Policy Identity
    policy_name = models.CharField(max_length=100, help_text="Policy name (e.g., 'Standard Consumer Loans')")
    description = models.TextField(help_text="Description of when to use this policy")
    is_default = models.BooleanField(default=False, help_text="Default policy for new loans")
    
    # Allocation Rules
    allocation_method = models.CharField(max_length=20, choices=ALLOCATION_METHOD, default='interest_first')
    allow_customer_directed = models.BooleanField(default=False)
    prepayment_to_principal = models.BooleanField(default=True)
    
    # Late Fee Rules
    grace_period_days = models.IntegerField(default=10, help_text="Days before late fees are assessed")
    late_fee_amount = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('25.00'),
        help_text="Fixed late fee amount"
    )
    late_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=Decimal('0.05'),
        help_text="Late fee as percentage of payment amount (0.05 = 5%)"
    )
    use_percentage_fee = models.BooleanField(default=False, help_text="Use percentage fee instead of fixed amount")
    max_late_fee = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('100.00'),
        help_text="Maximum late fee amount when using percentage"
    )
    
    # Payment Posting Rules
    weekend_posting = models.CharField(max_length=25, choices=WEEKEND_POSTING, default='next_business_day')
    cutoff_time = models.TimeField(default='17:00', help_text="Daily cutoff time for same-day posting")
    
    # Interest Calculation Rules
    daily_interest_calculation = models.BooleanField(default=True, help_text="Calculate interest daily vs monthly")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['company', '-is_default', 'policy_name']
        unique_together = [['company', 'policy_name']]
        indexes = [
            models.Index(fields=['company', 'is_default', 'is_active']),
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        default_text = " (Default)" if self.is_default else ""
        return f"{self.policy_name}{default_text} - {self.company.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default policy per company
        if self.is_default:
            PaymentPolicy.objects.filter(
                company=self.company, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class PaymentProcessor:
    """Industry-standard payment processing service with allocation logic"""
    
    def __init__(self, company=None, policy=None):
        self.company = company
        self.policy = policy or self._get_default_policy(company)
    
    def _get_default_policy(self, company):
        """Get default payment policy for company"""
        if company:
            try:
                return PaymentPolicy.objects.get(company=company, is_default=True, is_active=True)
            except PaymentPolicy.DoesNotExist:
                pass
        
        # Return basic default policy
        return type('DefaultPolicy', (), {
            'allocation_method': 'interest_first',
            'grace_period_days': 10,
            'late_fee_amount': Decimal('25.00'),
            'use_percentage_fee': False,
            'prepayment_to_principal': True,
        })()
    
    def calculate_allocation(self, loan, payment_amount, as_of_date=None):
        """
        Calculate how payment should be allocated according to industry standards
        Returns dict with allocation breakdown
        """
        from django.utils import timezone
        
        if as_of_date is None:
            as_of_date = timezone.now().date()
        
        allocation = {
            'late_fees': Decimal('0.00'),
            'accrued_interest': Decimal('0.00'),
            'current_interest': Decimal('0.00'),
            'principal': Decimal('0.00'),
            'prepayment': Decimal('0.00'),
            'total_allocated': Decimal('0.00'),
            'remaining_amount': payment_amount,
            'allocation_order': []
        }
        
        remaining = Decimal(str(payment_amount))
        
        # Step 1: Assess and collect late fees first
        late_fees = self._calculate_late_fees(loan, as_of_date)
        if late_fees > 0 and remaining > 0:
            fee_payment = min(late_fees, remaining)
            allocation['late_fees'] = fee_payment
            remaining -= fee_payment
            allocation['allocation_order'].append(f"Late Fees: ${fee_payment}")
        
        # Step 2: Collect accrued unpaid interest
        accrued_interest = self._calculate_accrued_interest(loan, as_of_date)
        if accrued_interest > 0 and remaining > 0:
            interest_payment = min(accrued_interest, remaining)
            allocation['accrued_interest'] = interest_payment
            remaining -= interest_payment
            allocation['allocation_order'].append(f"Accrued Interest: ${interest_payment}")
        
        # Step 3: Collect current period interest
        current_interest = self._calculate_current_interest(loan, as_of_date)
        if current_interest > 0 and remaining > 0:
            current_payment = min(current_interest, remaining)
            allocation['current_interest'] = current_payment
            remaining -= current_payment
            allocation['allocation_order'].append(f"Current Interest: ${current_payment}")
        
        # Step 4: Apply to principal balance
        if remaining > 0:
            principal_balance = loan.current_balance or Decimal('0.00')
            principal_payment = min(principal_balance, remaining)
            allocation['principal'] = principal_payment
            remaining -= principal_payment
            allocation['allocation_order'].append(f"Principal: ${principal_payment}")
        
        # Step 5: Handle prepayment (if enabled)
        if remaining > 0 and self.policy.prepayment_to_principal:
            allocation['prepayment'] = remaining
            allocation['allocation_order'].append(f"Prepayment: ${remaining}")
            remaining = Decimal('0.00')
        
        allocation['total_allocated'] = payment_amount - remaining
        allocation['remaining_amount'] = remaining
        
        return allocation
    
    def _calculate_late_fees(self, loan, as_of_date):
        """Calculate total late fees owed on loan"""
        # Get all overdue scheduled payments
        overdue_payments = loan.scheduled_payments.filter(
            status__in=['overdue', 'partial'],
            due_date__lt=as_of_date
        )
        
        total_late_fees = Decimal('0.00')
        for payment in overdue_payments:
            if payment.days_overdue >= self.policy.grace_period_days:
                # Calculate late fee if not already assessed
                if payment.late_fees_assessed == 0:
                    if self.policy.use_percentage_fee:
                        fee = payment.total_amount * self.policy.late_fee_percentage
                        fee = min(fee, self.policy.max_late_fee)
                    else:
                        fee = self.policy.late_fee_amount
                    total_late_fees += fee
                else:
                    # Add already assessed but unpaid late fees
                    total_late_fees += payment.late_fees_assessed
        
        return total_late_fees
    
    def _calculate_accrued_interest(self, loan, as_of_date):
        """Calculate accrued unpaid interest"""
        # For simplicity, return 0 for now
        # In production, this would calculate interest accrued since last payment
        return Decimal('0.00')
    
    def _calculate_current_interest(self, loan, as_of_date):
        """Calculate current period interest due"""
        # Get next scheduled payment
        next_payment = loan.scheduled_payments.filter(
            status='scheduled',
            due_date__gte=as_of_date
        ).first()
        
        if next_payment:
            return next_payment.interest_amount
        
        return Decimal('0.00')
    
    def process_payment(self, loan, payment_amount, payment_date, payment_method, 
                       processed_by=None, notes='', data_source='manual', 
                       reconciliation_status='not_required'):
        """
        Process a payment with industry-standard allocation
        Returns Payment object and allocation details
        
        Args:
            data_source: 'manual', 'bulk_upload', 'reconciliation', 'api'
            reconciliation_status: 'not_required', 'pending', 'matched', 'final'
        """
        from django.db import transaction
        
        # Calculate allocation
        allocation = self.calculate_allocation(loan, payment_amount, payment_date)
        
        with transaction.atomic():
            # Create payment record
            payment = Payment.objects.create(
                company=self.company,
                loan=loan,
                customer=loan.customer,
                payment_date=payment_date,
                payment_amount=payment_amount,
                payment_method=payment_method,
                payment_type='regular',
                status='completed',
                processed_by=processed_by,
                notes=notes,
                net_payment_amount=payment_amount,  # Assuming no processing fees for now
                # === THREE-TIER SYSTEM FIELDS ===
                data_source=data_source,
                reconciliation_status=reconciliation_status,
                is_bank_verified=True if data_source == 'reconciliation' else False
            )
            
            # Create allocation records
            allocation_order = 1
            for item in allocation['allocation_order']:
                description = item
                if 'Late Fees' in item:
                    alloc_type = 'late_fee'
                    amount = allocation['late_fees']
                elif 'Accrued Interest' in item:
                    alloc_type = 'interest'
                    amount = allocation['accrued_interest']
                elif 'Current Interest' in item:
                    alloc_type = 'interest'
                    amount = allocation['current_interest']
                elif 'Principal' in item:
                    alloc_type = 'principal'
                    amount = allocation['principal']
                elif 'Prepayment' in item:
                    alloc_type = 'principal'
                    amount = allocation['prepayment']
                else:
                    continue
                
                if amount > 0:
                    PaymentAllocation.objects.create(
                        company=self.company,
                        payment=payment,
                        loan=loan,
                        allocation_type=alloc_type,
                        allocation_amount=amount,
                        allocation_order=allocation_order,
                        balance_before=loan.current_balance,
                        balance_after=loan.current_balance - amount if alloc_type == 'principal' else loan.current_balance,
                        description=description
                    )
                    allocation_order += 1
            
            # Update loan balance
            if allocation['principal'] + allocation['prepayment'] > 0:
                loan.current_balance -= (allocation['principal'] + allocation['prepayment'])
                loan.save()
            
            # Update scheduled payment status
            self._update_scheduled_payments(loan, payment, allocation)
            
            # Create payment history
            PaymentHistory.objects.create(
                company=self.company,
                payment=payment,
                action_type='completed',
                performed_by=processed_by,
                description=f"Payment processed with allocation: {', '.join(allocation['allocation_order'])}"
            )
        
        return payment, allocation
    
    def _update_scheduled_payments(self, loan, payment, allocation):
        """Update scheduled payment statuses based on payment allocation"""
        # Get next due payment
        next_payment = loan.scheduled_payments.filter(
            status__in=['scheduled', 'overdue', 'partial']
        ).order_by('due_date').first()
        
        if next_payment:
            total_payment_applied = allocation['current_interest'] + allocation['principal']
            
            if total_payment_applied >= next_payment.total_amount:
                # Payment covers full scheduled amount
                next_payment.status = 'paid'
                next_payment.amount_paid = next_payment.total_amount
                next_payment.payment_date = payment.payment_date
            elif total_payment_applied > 0:
                # Partial payment
                next_payment.status = 'partial'
                next_payment.amount_paid += total_payment_applied
            
            next_payment.save()