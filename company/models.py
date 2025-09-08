from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
import uuid

User = get_user_model()

class Company(models.Model):
    """
    Company model for multi-tenant accounting system
    """
    # Unique identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Company Information
    name = models.CharField(max_length=200, help_text="Official company name")
    legal_name = models.CharField(max_length=200, blank=True, help_text="Legal registered name if different")
    
    # Business Registration
    registration_number = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Business registration/license number"
    )
    tax_id = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Tax identification number (EIN, ABN, etc.)"
    )
    
    # Contact Information
    email = models.EmailField(blank=True, help_text="Primary company email")
    phone = models.CharField(
        max_length=20, 
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')],
        help_text="Primary phone number"
    )
    website = models.URLField(blank=True, help_text="Company website")
    
    # Address Information
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default="United States")
    
    # Financial Settings
    base_currency = models.CharField(
        max_length=3, 
        default="USD",
        help_text="Base currency code (USD, EUR, GBP, etc.)"
    )
    financial_year_start = models.DateField(
        null=True, 
        blank=True,
        help_text="Start date of financial year"
    )
    
    # Industry & Business Type
    BUSINESS_TYPES = [
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('corporation', 'Corporation'),
        ('s_corp', 'S Corporation'),
        ('nonprofit', 'Non-Profit'),
        ('other', 'Other'),
    ]
    business_type = models.CharField(
        max_length=50, 
        choices=BUSINESS_TYPES, 
        blank=True,
        help_text="Legal business structure"
    )
    
    industry = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Primary industry or sector"
    )
    
    # System Settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Company Logo/Branding
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def full_address(self):
        """Return formatted full address"""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country
        ]
        return ", ".join([part for part in address_parts if part])
    
    @property
    def display_name(self):
        """Return display name (legal name if available, otherwise name)"""
        return self.legal_name if self.legal_name else self.name


class UserCompanyRole(models.Model):
    """
    User-Company relationship with role-based access
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Administrator'),
        ('accountant', 'Accountant'),
        ('bookkeeper', 'Bookkeeper'),
        ('viewer', 'Viewer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_roles')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='user_roles')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    
    # Access permissions
    is_active = models.BooleanField(default=True)
    can_edit_settings = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'company']
        verbose_name = "User Company Role"
        verbose_name_plural = "User Company Roles"
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.get_role_display()})"


class UserCompanyPreference(models.Model):
    """
    User preferences for company interaction
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_preferences')
    active_company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Currently selected company"
    )
    
    # UI Preferences
    default_company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='default_for_users',
        help_text="Default company on login"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Company Preference"
        verbose_name_plural = "User Company Preferences"
    
    def __str__(self):
        return f"{self.user.username} preferences"
