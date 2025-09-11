from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Company(models.Model):
    """Enhanced Company model with setup integration"""

    name = models.CharField(max_length=100, help_text="Company name")
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_companies"
    )
    description = models.TextField(blank=True, help_text="Brief company description")
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)

    # Extended company information for setup
    legal_name = models.CharField(
        max_length=200, blank=True, help_text="Legal business name"
    )
    business_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("sole_proprietorship", "Sole Proprietorship"),
            ("partnership", "Partnership"),
            ("corporation", "Corporation"),
            ("llc", "Limited Liability Company"),
            ("nonprofit", "Non-Profit Organization"),
        ],
        help_text="Type of business entity",
    )
    industry = models.CharField(
        max_length=100, blank=True, help_text="Industry or business sector"
    )
    tax_id = models.CharField(max_length=50, blank=True, help_text="Tax ID / EIN / ABN")

    # Address information
    address = models.TextField(blank=True, help_text="Street address")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True, help_text="State/Province")
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="United States")

    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, help_text="Business email")
    website = models.URLField(blank=True)

    # Financial settings
    fiscal_year_start = models.DateField(
        null=True, blank=True, help_text="Start of fiscal year"
    )
    base_currency = models.CharField(
        max_length=3,
        default="USD",
        choices=[
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("GBP", "British Pound"),
            ("CAD", "Canadian Dollar"),
            ("AUD", "Australian Dollar"),
        ],
        help_text="Base currency for financial reporting",
    )

    # Setup status
    setup_complete = models.BooleanField(
        default=False, help_text="Company setup completed"
    )

    # Basic settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        """Return display name"""
        return self.legal_name or self.name

    @property
    def is_setup_complete(self):
        """Check if company setup is complete"""
        try:
            from setup.models import CompanySetupStatus

            setup_status = CompanySetupStatus.objects.get(company=self)
            return setup_status.completion_percentage >= 100
        except Exception:
            return False

    @property
    def setup_completion_percentage(self):
        """Get setup completion percentage"""
        try:
            from setup.models import CompanySetupStatus

            setup_status = CompanySetupStatus.objects.get(company=self)
            return setup_status.completion_percentage
        except Exception:
            return 0

    def get_essential_accounts(self):
        """Get essential accounts created during setup"""
        return self.account_set.filter(is_essential=True)

    def get_setup_tax_rates(self):
        """Get tax rates created during setup"""
        return self.taxrate_set.filter(setup_created=True)


class UserCompanyAccess(models.Model):
    """Simple User-Company access management"""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("user", "User"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="company_access"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="user_access"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "company"]
        verbose_name = "User Company Access"
        verbose_name_plural = "User Company Access"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.get_role_display()})"


class UserCompanyPreference(models.Model):
    """Simple user preferences for active company"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="company_preference"
    )
    active_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Currently active company",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Company Preference"
        verbose_name_plural = "User Company Preferences"

    def __str__(self):
        return f"{self.user.username} - Active: {self.active_company}"


# Auto-create preference when user is created
@receiver(post_save, sender=User)
def create_user_company_preference(sender, instance, created, **kwargs):
    if created:
        UserCompanyPreference.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_company_preference(sender, instance, **kwargs):
    try:
        instance.company_preference.save()
    except UserCompanyPreference.DoesNotExist:
        UserCompanyPreference.objects.create(user=instance)
