"""
Company-aware base models for loan management system.
"""
from django.db import models
from django.contrib.auth.models import User
from core.managers import CompanyAwareManager


class CompanyAwareLoanModel(models.Model):
    """
    Abstract base class for all loan models that need company isolation.
    Use this for ALL loan models to ensure proper multi-company separation.
    """
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        help_text="Company this record belongs to",
        verbose_name="Company"
    )
    
    # Use company-aware manager
    objects = CompanyAwareManager()
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['company']),
        ]


class AuditableLoanModel(models.Model):
    """
    Abstract base class for audit trail functionality in loan models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(app_label)s_%(class)s_created',
        help_text="User who created this record"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(app_label)s_%(class)s_updated',
        help_text="User who last updated this record"
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]


class BaseLoanModel(CompanyAwareLoanModel, AuditableLoanModel):
    """
    Combined base class with company isolation and audit trails.
    Use this as the base for all loan models that need both features.
    """
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['company', 'updated_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to handle updated_by field"""
        # The updated_by field should be set in views/forms
        super().save(*args, **kwargs)
    
    def __str__(self):
        """Default string representation including company info"""
        return f"{self.__class__.__name__} ({self.company.name})"
