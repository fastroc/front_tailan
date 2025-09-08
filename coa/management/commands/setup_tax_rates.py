from django.core.management.base import BaseCommand
from coa.models import TaxRate


class Command(BaseCommand):
    help = 'Create default tax rates for the COA system'

    def handle(self, *args, **options):
        tax_rates = [
            {
                'name': 'Sales Tax on Imports',
                'rate': 0.0000,
                'description': 'Sales Tax on Imports (0%)',
            },
            {
                'name': 'Tax Exempt',
                'rate': 0.0000,
                'description': 'Tax Exempt (0%)',
            },
            {
                'name': 'Tax on Purchases',
                'rate': 0.0000,
                'description': 'Tax on Purchases (0%)',
            },
            {
                'name': 'Tax on Sales',
                'rate': 0.0000,
                'description': 'Tax on Sales (0%)',
            },
        ]

        created_count = 0
        for tax_data in tax_rates:
            tax_rate, created = TaxRate.objects.get_or_create(
                name=tax_data['name'],
                defaults={
                    'rate': tax_data['rate'],
                    'description': tax_data['description'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tax rate: {tax_rate.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tax rate already exists: {tax_rate.name}')
                )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} tax rates')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No new tax rates were created')
            )
