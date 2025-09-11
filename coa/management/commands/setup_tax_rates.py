from django.core.management.base import BaseCommand
from coa.models import TaxRate
from company.models import Company


class Command(BaseCommand):
    help = "Create default system tax rates for all companies"

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=int,
            help="Create tax rates for specific company ID only",
        )

    def handle(self, *args, **options):
        company_id = options.get("company_id")

        if company_id:
            try:
                companies = [Company.objects.get(id=company_id)]
                self.stdout.write(
                    f"Creating tax rates for company: {companies[0].name}"
                )
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Company with ID {company_id} does not exist")
                )
                return
        else:
            companies = Company.objects.filter(is_active=True)
            self.stdout.write(
                f"Creating tax rates for {companies.count()} active companies"
            )

        total_created = 0

        for company in companies:
            self.stdout.write(f"\n--- Processing company: {company.name} ---")
            created_rates = TaxRate.create_default_tax_rates(company)

            if created_rates:
                total_created += len(created_rates)
                for tax_rate in created_rates:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created: {tax_rate.name} ({tax_rate.rate * 100}%)"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Default tax rates already exist for this company"
                    )
                )

        if total_created > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully created {total_created} system tax rates"
                )
            )
        else:
            self.stdout.write(self.style.WARNING("\nNo new tax rates were created"))
