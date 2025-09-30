from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ReportConfiguration(models.Model):
    """
    Store user-specific report configurations and preferences
    """
    REPORT_TYPES = [
        ('portfolio', 'Portfolio Overview'),
        ('aging', 'Aging Analysis'),
        ('performance', 'Performance Metrics'),
        ('risk', 'Risk Assessment'),
        ('monthly', 'Monthly Trends'),
        ('customer', 'Customer Analysis'),
    ]
    
    DATE_RANGES = [
        ('7d', 'Last 7 Days'),
        ('30d', 'Last 30 Days'),
        ('90d', 'Last 90 Days'),
        ('1y', 'Last Year'),
        ('ytd', 'Year to Date'),
        ('custom', 'Custom Range'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    name = models.CharField(max_length=100)
    date_range = models.CharField(max_length=10, choices=DATE_RANGES, default='30d')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict, help_text="Store additional filters as JSON")
    is_active = models.BooleanField(default=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Report Configuration"
        verbose_name_plural = "Report Configurations"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportCache(models.Model):
    """
    Cache expensive report calculations to improve performance
    """
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50)
    cache_key = models.CharField(max_length=200, unique=True)
    data = models.JSONField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Report Cache"
        verbose_name_plural = "Report Cache"
        indexes = [
            models.Index(fields=['company', 'report_type']),
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"Cache: {self.report_type} - {self.company.name}"


class ReportExport(models.Model):
    """
    Track report exports and provide download links
    """
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50)
    format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    parameters = models.JSONField(default=dict)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Report Export"
        verbose_name_plural = "Report Exports"
        ordering = ['-created_at']
    
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at
    
    def __str__(self):
        return f"{self.get_format_display()} export - {self.report_type}"


class ReportSchedule(models.Model):
    """
    Schedule automatic report generation and delivery
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    report_config = models.ForeignKey(ReportConfiguration, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    email_recipients = models.TextField(help_text="Comma-separated email addresses")
    next_run = models.DateTimeField()
    last_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Report Schedule"
        verbose_name_plural = "Report Schedules"
        ordering = ['next_run']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
