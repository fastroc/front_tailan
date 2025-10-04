"""
📊 ANALYTICS MODELS
Performance Tracking & Business Intelligence for SMART Creditor
"""

from django.db import models
from django.contrib.auth.models import User


class ReconciliationMetrics(models.Model):
    """
    Daily metrics for reconciliation performance and AI effectiveness
    Used to track system performance over time
    """
    date = models.DateField(help_text="Date for these metrics")
    
    # Volume metrics
    total_transactions = models.IntegerField(
        default=0,
        help_text="Total transactions processed"
    )
    manually_matched = models.IntegerField(
        default=0,
        help_text="Matched without AI/rule help"
    )
    rule_matched = models.IntegerField(
        default=0,
        help_text="Matched using bank rules"
    )
    ai_matched = models.IntegerField(
        default=0,
        help_text="Matched using AI patterns"
    )
    hybrid_matched = models.IntegerField(
        default=0,
        help_text="Matched using both rules and AI"
    )
    unmatched = models.IntegerField(
        default=0,
        help_text="Still unmatched"
    )
    
    # Efficiency metrics
    avg_time_per_transaction = models.FloatField(
        default=0.0, 
        help_text="Average seconds per transaction"
    )
    total_time_saved = models.FloatField(
        default=0.0, 
        help_text="Total hours saved by automation"
    )
    automation_rate = models.FloatField(
        default=0.0, 
        help_text="Percentage auto-matched (0-100)"
    )
    
    # Quality metrics
    ai_accuracy = models.FloatField(
        default=0.0, 
        help_text="% of AI suggestions accepted"
    )
    rule_accuracy = models.FloatField(
        default=0.0, 
        help_text="% of rule suggestions accepted"
    )
    user_corrections = models.IntegerField(
        default=0, 
        help_text="Number of user modifications to suggestions"
    )
    
    # Financial metrics
    total_amount_reconciled = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text="Total monetary amount reconciled"
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='reconciliation_metrics',
        null=True, 
        blank=True
    )
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_reconciliation_metrics'
        unique_together = [['date', 'company']]
        ordering = ['-date']
        verbose_name = 'Reconciliation Metrics'
        verbose_name_plural = 'Reconciliation Metrics'
        indexes = [
            models.Index(fields=['company', '-date']),
            models.Index(fields=['-date']),
        ]
    
    def __str__(self):
        return f"{self.date} | {self.automation_rate:.1f}% automated | {self.total_transactions} trans"
    
    @property
    def efficiency_score(self):
        """
        Overall efficiency score 0-100
        Weighted combination of automation, accuracy, and speed
        """
        # 50% weight: automation rate
        auto_score = self.automation_rate * 0.5
        
        # 30% weight: AI accuracy
        accuracy_score = self.ai_accuracy * 0.3
        
        # 20% weight: speed (60 seconds = 100%, slower = lower score)
        if self.avg_time_per_transaction > 0:
            speed_score = min((60 / self.avg_time_per_transaction) * 100, 100) * 0.2
        else:
            speed_score = 0
        
        return round(auto_score + accuracy_score + speed_score, 1)
    
    @property
    def time_saved_display(self):
        """Human-readable time saved"""
        if self.total_time_saved >= 1:
            return f"{self.total_time_saved:.1f} hours"
        else:
            return f"{self.total_time_saved * 60:.0f} minutes"


class UserPerformance(models.Model):
    """
    Individual user performance tracking for reconciliation tasks
    Helps identify top performers and training needs
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Volume
    transactions_processed = models.IntegerField(
        default=0,
        help_text="Number of transactions processed"
    )
    
    # Speed metrics
    avg_time_per_transaction = models.FloatField(
        default=0.0, 
        help_text="Average seconds per transaction"
    )
    fastest_match = models.FloatField(
        default=0.0, 
        help_text="Fastest match time in seconds"
    )
    slowest_match = models.FloatField(
        default=0.0, 
        help_text="Slowest match time in seconds"
    )
    
    # Quality metrics
    accepted_suggestions = models.IntegerField(
        default=0,
        help_text="Number of AI/rule suggestions accepted"
    )
    rejected_suggestions = models.IntegerField(
        default=0,
        help_text="Number of AI/rule suggestions rejected"
    )
    manual_matches = models.IntegerField(
        default=0,
        help_text="Number of purely manual matches"
    )
    
    # AI usage
    ai_usage_rate = models.FloatField(
        default=0.0, 
        help_text="% of time using AI/rule suggestions (0-100)"
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='user_performance',
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'analytics_user_performance'
        unique_together = [['user', 'date', 'company']]
        ordering = ['-date', 'user']
        verbose_name = 'User Performance'
        verbose_name_plural = 'User Performance Records'
    
    def __str__(self):
        return f"{self.user.username} | {self.date} | {self.transactions_processed} trans"
    
    @property
    def productivity_score(self):
        """Overall productivity score 0-100"""
        if self.transactions_processed == 0:
            return 0
        
        # More transactions = better (normalize to 50 trans/day = 100%)
        volume_score = min((self.transactions_processed / 50) * 100, 100) * 0.4
        
        # Faster = better (normalize to 60 sec/trans = 100%)
        if self.avg_time_per_transaction > 0:
            speed_score = min((60 / self.avg_time_per_transaction) * 100, 100) * 0.3
        else:
            speed_score = 0
        
        # Higher AI usage = better (using tools efficiently)
        ai_usage_score = self.ai_usage_rate * 0.3
        
        return round(volume_score + speed_score + ai_usage_score, 1)


class PatternAnalytics(models.Model):
    """
    Analytics on individual AI pattern performance over time
    Tracks which patterns are working well
    """
    pattern = models.ForeignKey(
        'smart_learning.MatchPattern', 
        on_delete=models.CASCADE, 
        related_name='daily_analytics'
    )
    date = models.DateField()
    
    # Usage metrics
    times_suggested = models.IntegerField(
        default=0,
        help_text="How many times suggested today"
    )
    times_accepted = models.IntegerField(
        default=0,
        help_text="How many times accepted"
    )
    times_rejected = models.IntegerField(
        default=0,
        help_text="How many times rejected"
    )
    times_modified = models.IntegerField(
        default=0,
        help_text="How many times modified"
    )
    
    # Performance metrics
    acceptance_rate = models.FloatField(
        default=0.0,
        help_text="Acceptance rate % for this day"
    )
    avg_confidence = models.FloatField(
        default=0.0,
        help_text="Average confidence score when suggested"
    )
    avg_response_time = models.FloatField(
        default=0.0, 
        help_text="Average user response time in seconds"
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='pattern_analytics',
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'analytics_pattern_performance'
        unique_together = [['pattern', 'date', 'company']]
        ordering = ['-date']
        verbose_name = 'Pattern Analytics'
        verbose_name_plural = 'Pattern Analytics'
    
    def __str__(self):
        return f"{self.pattern.pattern_name} | {self.date} | {self.acceptance_rate:.1f}% accepted"


class SystemHealth(models.Model):
    """
    Overall system health monitoring and AI model performance
    Daily snapshot of system status
    """
    date = models.DateField()
    
    # AI Model performance
    model_accuracy = models.FloatField(
        default=0.0, 
        help_text="Overall AI accuracy %"
    )
    model_precision = models.FloatField(
        default=0.0, 
        help_text="AI precision % (true positives / all positives)"
    )
    model_recall = models.FloatField(
        default=0.0, 
        help_text="AI recall % (true positives / all actual positives)"
    )
    f1_score = models.FloatField(
        default=0.0,
        help_text="F1 score (harmonic mean of precision and recall)"
    )
    
    # Data quality metrics
    training_data_size = models.IntegerField(
        default=0, 
        help_text="Number of historical matches available for training"
    )
    pattern_count = models.IntegerField(
        default=0,
        help_text="Total number of patterns"
    )
    active_patterns = models.IntegerField(
        default=0,
        help_text="Number of active patterns"
    )
    
    # System usage
    active_users = models.IntegerField(
        default=0,
        help_text="Number of users active today"
    )
    api_calls = models.IntegerField(
        default=0,
        help_text="Number of API calls made"
    )
    avg_response_time = models.FloatField(
        default=0.0, 
        help_text="Average API response time in milliseconds"
    )
    
    # Issues & alerts
    errors_count = models.IntegerField(
        default=0,
        help_text="Number of errors encountered"
    )
    warnings_count = models.IntegerField(
        default=0,
        help_text="Number of warnings generated"
    )
    
    # Multi-tenancy
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE, 
        related_name='system_health',
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'analytics_system_health'
        unique_together = [['date', 'company']]
        ordering = ['-date']
        verbose_name = 'System Health'
        verbose_name_plural = 'System Health Records'
    
    def __str__(self):
        return f"{self.date} | Accuracy: {self.model_accuracy:.1f}% | {self.active_patterns} patterns"
    
    @property
    def health_status(self):
        """Overall health status indicator"""
        if self.model_accuracy >= 85 and self.errors_count == 0:
            return "Excellent"
        elif self.model_accuracy >= 70 and self.errors_count < 5:
            return "Good"
        elif self.model_accuracy >= 50 and self.errors_count < 10:
            return "Fair"
        else:
            return "Needs Attention"
    
    @property
    def is_data_sufficient(self):
        """Check if we have enough training data"""
        return self.training_data_size >= 50  # Minimum 50 samples recommended

