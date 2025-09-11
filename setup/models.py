from django.db import models
from company.models import Company


class CompanySetupStatus(models.Model):
    """Track company setup completion status with detailed progress"""

    # Company relationship
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        verbose_name="Company",
        related_name="setup_status",
    )

    # Setup step completion flags
    company_info_complete = models.BooleanField(
        default=False,
        verbose_name="Company Info Complete",
        help_text="Company information setup completed",
    )

    accounts_complete = models.BooleanField(
        default=False,
        verbose_name="Essential Accounts Complete",
        help_text="Essential accounts created",
    )

    tax_complete = models.BooleanField(
        default=False,
        verbose_name="Tax Configuration Complete",
        help_text="Tax rates configured (optional step)",
    )

    balance_complete = models.BooleanField(
        default=False,
        verbose_name="Opening Balances Complete",
        help_text="Opening balances entered",
    )

    # Setup timestamps
    setup_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Setup Started At",
        help_text="When setup process was first started",
    )

    setup_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Setup Completed At",
        help_text="When setup process was completed",
    )

    # Progress tracking
    current_step = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Current Step",
        help_text="Current setup step being worked on",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Setup Notes",
        help_text="Internal notes about setup process",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Setup Status"
        verbose_name_plural = "Company Setup Statuses"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.company.name} - {self.completion_percentage}% Complete"

    @property
    def completion_percentage(self):
        """Calculate completion percentage based on completed steps"""
        # Required steps: company_info (25%), accounts (35%), opening_balance (25%) = 85%
        # Optional step: tax_setup (15%) = 100%

        percentage = 0

        if self.company_info_complete:
            percentage += 25

        if self.accounts_complete:
            percentage += 35

        if self.balance_complete:
            percentage += 25

        if self.tax_complete:
            percentage += 15

        return min(percentage, 100)  # Cap at 100%

    @property
    def next_step(self):
        """Determine next setup step to complete"""
        if not self.company_info_complete:
            return "company_info"
        elif not self.accounts_complete:
            return "essential_accounts"
        elif not self.balance_complete:
            return "opening_balance"
        elif not self.tax_complete:
            return "tax_setup"  # Optional step
        else:
            return "complete"

    @property
    def required_steps_complete(self):
        """Check if all required steps are complete"""
        return (
            self.company_info_complete
            and self.accounts_complete
            and self.balance_complete
        )

    @property
    def all_steps_complete(self):
        """Check if all steps (including optional) are complete"""
        return (
            self.company_info_complete
            and self.accounts_complete
            and self.tax_complete
            and self.balance_complete
        )

    def save(self, *args, **kwargs):
        """Override save to auto-update related fields"""
        # Set setup started timestamp
        if not self.setup_started_at and self.completion_percentage > 0:
            from django.utils import timezone

            self.setup_started_at = timezone.now()

        # Set completion timestamp when required steps complete
        if self.required_steps_complete and not self.setup_completed_at:
            from django.utils import timezone

            self.setup_completed_at = timezone.now()
            self.company.setup_complete = True
            self.company.save(update_fields=["setup_complete"])

        super().save(*args, **kwargs)

    def mark_step_complete(self, step_name):
        """Mark a specific setup step as complete"""
        step_mapping = {
            "company_info": "company_info_complete",
            "essential_accounts": "accounts_complete",
            "tax_setup": "tax_complete",
            "opening_balance": "balance_complete",
        }

        if step_name in step_mapping:
            setattr(self, step_mapping[step_name], True)
            self.current_step = self.next_step
            self.save()
            return True
        return False

    def get_completion_summary(self):
        """Get detailed completion summary"""
        return {
            "company_info": {
                "complete": self.company_info_complete,
                "name": "Company Information",
                "required": True,
                "weight": 25,
            },
            "essential_accounts": {
                "complete": self.accounts_complete,
                "name": "Essential Accounts",
                "required": True,
                "weight": 35,
            },
            "opening_balance": {
                "complete": self.balance_complete,
                "name": "Opening Balances",
                "required": True,
                "weight": 25,
            },
            "tax_setup": {
                "complete": self.tax_complete,
                "name": "Tax Configuration",
                "required": False,
                "weight": 15,
            },
        }
