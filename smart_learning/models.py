"""
🧠 SMART LEARNING MODELS
AI Pattern Recognition & Machine Learning for Transaction Matching
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class MatchPattern(models.Model):
    """
    Learned patterns from historical transaction matches
    Example: "KHAN BANK FEE" → WHO: "Bank Fee", WHAT: "Bank Charges"
    
    This is the core AI model that learns from user behavior
    """
    # Pattern identification
    pattern_name = models.CharField(
        max_length=255, 
        unique=True, 
        help_text="Human-readable pattern name"
    )
    pattern_type = models.CharField(
        max_length=20, 
        choices=[
            ('exact', 'Exact Match'),
            ('contains', 'Contains Keyword'),
            ('regex', 'Regular Expression'),
            ('fuzzy', 'Fuzzy Match'),
            ('ml', 'ML Prediction'),
        ], 
        default='contains',
        help_text="Type of pattern matching algorithm"
    )
    
    # Pattern definition
    description_pattern = models.TextField(
        help_text="What to look for in transaction description"
    )
    amount_min = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Minimum amount (optional constraint)"
    )
    amount_max = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Maximum amount (optional constraint)"
    )
    transaction_type = models.CharField(
        max_length=10, 
        null=True, 
        blank=True, 
        choices=[
            ('debit', 'Debit'),
            ('credit', 'Credit'),
        ],
        help_text="Filter by transaction type"
    )
    
    # Suggested mapping
    suggested_who = models.CharField(
        max_length=255, 
        help_text="Suggested WHO (contact/payee name)"
    )
    suggested_what = models.ForeignKey(
        'coa.Account', 
        on_delete=models.PROTECT, 
        help_text="Suggested WHAT (Chart of Account)",
        related_name='pattern_suggestions'
    )
    
    # Pattern quality metrics (updated through learning)
    times_seen = models.IntegerField(
        default=0, 
        help_text="How many times this pattern appeared"
    )
    times_accepted = models.IntegerField(
        default=0, 
        help_text="How many times user accepted the suggestion"
    )
    times_rejected = models.IntegerField(
        default=0, 
        help_text="How many times user rejected the suggestion"
    )
    accuracy_rate = models.FloatField(
        default=0.0, 
        help_text="Acceptance rate percentage (0-100)"
    )
    
    # Confidence scoring
    confidence = models.FloatField(
        default=50.0, 
        help_text="Pattern confidence score 0-100%"
    )
    
    # Status flags
    is_active = models.BooleanField(
        default=True, 
        help_text="Is this pattern active and should be used?"
    )
    auto_apply = models.BooleanField(
        default=False, 
        help_text="Auto-apply this pattern if confidence >90%"
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='smart_patterns',
        null=True, 
        blank=True,
        help_text="Company this pattern belongs to"
    )
    
    # Metadata & audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_patterns'
    )
    last_trained = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this pattern was last retrained"
    )
    
    class Meta:
        db_table = 'smart_match_pattern'
        ordering = ['-accuracy_rate', '-times_seen']
        indexes = [
            models.Index(fields=['is_active', '-accuracy_rate']),
            models.Index(fields=['pattern_type']),
            models.Index(fields=['company', 'is_active']),
        ]
        verbose_name = 'Match Pattern'
        verbose_name_plural = 'Match Patterns'
    
    def __str__(self):
        return f"{self.pattern_name} ({self.accuracy_rate:.1f}% accurate, used {self.times_seen}x)"
    
    def update_metrics(self):
        """
        Recalculate accuracy and confidence after receiving feedback
        This is the core learning mechanism
        """
        total = self.times_accepted + self.times_rejected
        if total > 0:
            # Calculate accuracy rate
            self.accuracy_rate = (self.times_accepted / total) * 100
            
            # Update confidence based on accuracy and volume
            # More data = more confidence in the accuracy
            volume_weight = min(total / 10, 1.0)  # Max confidence at 10+ samples
            self.confidence = self.accuracy_rate * volume_weight
            
            # Auto-enable auto_apply for very high accuracy patterns
            if self.accuracy_rate >= 95.0 and total >= 10:
                self.auto_apply = True
            elif self.accuracy_rate < 85.0:
                self.auto_apply = False
        
        self.last_trained = timezone.now()
        self.save()
    
    @property
    def is_well_trained(self):
        """Check if pattern has enough data to be reliable"""
        return (self.times_seen + self.times_accepted + self.times_rejected) >= 5
    
    @property
    def success_rate_display(self):
        """Human-readable success rate"""
        if self.accuracy_rate >= 90:
            return f"Excellent ({self.accuracy_rate:.1f}%)"
        elif self.accuracy_rate >= 75:
            return f"Good ({self.accuracy_rate:.1f}%)"
        elif self.accuracy_rate >= 60:
            return f"Fair ({self.accuracy_rate:.1f}%)"
        else:
            return f"Poor ({self.accuracy_rate:.1f}%)"


class TransactionMatchHistory(models.Model):
    """
    Records every transaction match (manual, rule, or AI)
    This is our training data for machine learning
    """
    # Transaction snapshot (at time of matching)
    transaction_date = models.DateField()
    transaction_description = models.TextField()
    transaction_amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(
        max_length=10, 
        choices=[
            ('debit', 'Debit'),
            ('credit', 'Credit'),
        ]
    )
    
    # What was matched (the answer)
    matched_who = models.CharField(
        max_length=255, 
        help_text="Customer/vendor name matched"
    )
    matched_what = models.ForeignKey(
        'coa.Account', 
        on_delete=models.PROTECT, 
        help_text="Chart of Account matched",
        related_name='match_history'
    )
    
    # How it was matched (the source)
    match_source = models.CharField(
        max_length=20, 
        choices=[
            ('manual', 'Manual Entry'),
            ('rule', 'Bank Rule'),
            ('pattern', 'AI Pattern'),
            ('hybrid', 'Rule + AI'),
        ], 
        default='manual'
    )
    
    # If from rule or pattern, link to it
    bank_rule = models.ForeignKey(
        'bank_rules.BankRule', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='match_history'
    )
    match_pattern = models.ForeignKey(
        MatchPattern, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='usage_history'
    )
    
    # Confidence & feedback
    confidence_score = models.FloatField(
        default=0.0, 
        help_text="Confidence score 0-100%"
    )
    user_accepted = models.BooleanField(
        null=True, 
        blank=True, 
        help_text="Did user accept the suggestion as-is?"
    )
    user_modified = models.BooleanField(
        default=False, 
        help_text="Did user modify the suggestion?"
    )
    
    # Link to actual reconciliation record
    transaction_match = models.ForeignKey(
        'reconciliation.TransactionMatch', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='learning_history'
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='transaction_match_history',
        null=True, 
        blank=True
    )
    
    # Metadata
    matched_by = models.ForeignKey(User, on_delete=models.PROTECT)
    matched_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'smart_match_history'
        ordering = ['-matched_at']
        indexes = [
            models.Index(fields=['transaction_date']),
            models.Index(fields=['matched_who']),
            models.Index(fields=['match_source']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['company', '-matched_at']),
            models.Index(fields=['user_accepted']),
        ]
        verbose_name = 'Transaction Match History'
        verbose_name_plural = 'Transaction Match Histories'
    
    def __str__(self):
        return f"{self.transaction_date} | {self.transaction_description[:50]} → {self.matched_who}"


class MatchFeedback(models.Model):
    """
    User feedback on AI/rule suggestions
    Used for continuous learning and improvement
    """
    match_history = models.ForeignKey(
        TransactionMatchHistory, 
        on_delete=models.CASCADE, 
        related_name='feedbacks'
    )
    
    # What was suggested
    suggested_who = models.CharField(max_length=255)
    suggested_what = models.ForeignKey(
        'coa.Account', 
        on_delete=models.PROTECT, 
        related_name='feedback_as_suggestion'
    )
    suggestion_source = models.CharField(
        max_length=20, 
        choices=[
            ('rule', 'Bank Rule'),
            ('pattern', 'AI Pattern'),
            ('hybrid', 'Hybrid'),
        ]
    )
    confidence_score = models.FloatField()
    
    # What user did
    action = models.CharField(
        max_length=20, 
        choices=[
            ('accepted', 'Accepted as-is'),
            ('modified', 'Modified suggestion'),
            ('rejected', 'Rejected entirely'),
        ]
    )
    
    # If modified, what changed
    actual_who = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="What user actually entered for WHO"
    )
    actual_what = models.ForeignKey(
        'coa.Account', 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT, 
        related_name='feedback_as_actual',
        help_text="What user actually selected for WHAT"
    )
    
    # UX metrics
    response_time_seconds = models.IntegerField(
        null=True, 
        blank=True,
        help_text="How long user took to decide"
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='match_feedbacks',
        null=True, 
        blank=True
    )
    
    # Metadata
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'smart_match_feedback'
        ordering = ['-created_at']
        verbose_name = 'Match Feedback'
        verbose_name_plural = 'Match Feedbacks'
    
    def __str__(self):
        return f"{self.action} | {self.suggested_who} → {self.actual_who or 'N/A'}"


class ConfidenceScore(models.Model):
    """
    Tracks confidence score accuracy over time (meta-learning)
    Used to calibrate the confidence scores themselves
    
    Example: If we say 80% confidence, are we actually right 80% of the time?
    """
    confidence_range = models.CharField(
        max_length=20, 
        choices=[
            ('0-20', 'Very Low (0-20%)'),
            ('20-40', 'Low (20-40%)'),
            ('40-60', 'Medium (40-60%)'),
            ('60-80', 'High (60-80%)'),
            ('80-100', 'Very High (80-100%)'),
        ]
    )
    
    # Actual performance in this range
    total_suggestions = models.IntegerField(
        default=0,
        help_text="How many suggestions made in this confidence range"
    )
    accepted_suggestions = models.IntegerField(
        default=0,
        help_text="How many were accepted"
    )
    actual_accuracy = models.FloatField(
        default=0.0,
        help_text="Actual acceptance rate %"
    )
    
    # Calibration metric
    calibration_error = models.FloatField(
        default=0.0,
        help_text="Difference between predicted and actual confidence"
    )
    
    # Time period
    date = models.DateField()
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='confidence_scores',
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'smart_confidence_score'
        unique_together = [['confidence_range', 'date', 'company']]
        ordering = ['-date']
        verbose_name = 'Confidence Score'
        verbose_name_plural = 'Confidence Scores'
    
    def __str__(self):
        return f"{self.confidence_range} | {self.actual_accuracy:.1f}% actual (expected {self.get_expected_confidence()}%)"
    
    def get_expected_confidence(self):
        """Get the midpoint of the confidence range"""
        range_map = {
            '0-20': 10,
            '20-40': 30,
            '40-60': 50,
            '60-80': 70,
            '80-100': 90,
        }
        return range_map.get(self.confidence_range, 50)
    
    def update_calibration(self):
        """Calculate how well-calibrated our confidence scores are"""
        if self.total_suggestions > 0:
            self.actual_accuracy = (self.accepted_suggestions / self.total_suggestions) * 100
            expected = self.get_expected_confidence()
            self.calibration_error = abs(self.actual_accuracy - expected)
        self.save()

