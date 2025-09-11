from django.db.models.signals import post_save
from django.dispatch import receiver
from company.models import Company
from coa.models import TaxRate


@receiver(post_save, sender=Company)
def create_default_tax_rates_for_company(sender, instance, created, **kwargs):
    """
    Automatically create default system tax rates when a new company is created.
    """
    if created and instance.is_active:
        # Create default tax rates for the new company
        created_rates = TaxRate.create_default_tax_rates(instance)

        if created_rates:
            print(
                f"✅ Created {len(created_rates)} default tax rates for company: {instance.name}"
            )
