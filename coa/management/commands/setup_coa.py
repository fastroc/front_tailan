from django.core.management.base import BaseCommand
from coa.models import TaxRate, Account, AccountType


class Command(BaseCommand):
    help = 'Setup initial COA data including tax rates and sample accounts'

    def handle(self, *args, **options):
        # Create default tax rates
        self.stdout.write('Setting up tax rates...')
        tax_rates = [
            {'name': 'Tax Exempt', 'rate': 0.0000, 'description': 'Tax exempt accounts (0%)'},
            {'name': 'Standard Rate', 'rate': 0.1500, 'description': 'Standard tax rate (15%)'},
            {'name': 'Reduced Rate', 'rate': 0.0750, 'description': 'Reduced tax rate (7.5%)'},
            {'name': 'High Rate', 'rate': 0.2500, 'description': 'High tax rate (25%)'},
            {'name': 'VAT Standard', 'rate': 0.2000, 'description': 'VAT standard rate (20%)'},
        ]
        
        created_tax_rates = {}
        for rate_data in tax_rates:
            tax_rate, created = TaxRate.objects.get_or_create(
                name=rate_data['name'],
                defaults={
                    'rate': rate_data['rate'],
                    'description': rate_data['description']
                }
            )
            created_tax_rates[rate_data['name']] = tax_rate
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created tax rate: {tax_rate.name} ({tax_rate.percentage_display})')
                )
            else:
                self.stdout.write(f'→ Tax rate already exists: {tax_rate.name}')
        
        # Create sample accounts
        self.stdout.write('\nSetting up sample accounts...')
        
        # Get tax exempt rate for sample accounts
        tax_exempt = created_tax_rates['Tax Exempt']
        standard_rate = created_tax_rates['Standard Rate']
        
        sample_accounts = [
            # Assets
            {'code': '1000', 'name': 'Cash', 'type': 'ASSET', 'tax_rate': tax_exempt, 'ytd': 10000.00},
            {'code': '1100', 'name': 'Accounts Receivable', 'type': 'ASSET', 'tax_rate': tax_exempt, 'ytd': 5000.00},
            {'code': '1200', 'name': 'Inventory', 'type': 'ASSET', 'tax_rate': standard_rate, 'ytd': 15000.00},
            
            # Liabilities
            {'code': '2000', 'name': 'Accounts Payable', 'type': 'LIABILITY', 'tax_rate': tax_exempt, 'ytd': 3000.00},
            {'code': '2100', 'name': 'Notes Payable', 'type': 'LIABILITY', 'tax_rate': tax_exempt, 'ytd': 8000.00},
            
            # Equity
            {'code': '3000', 'name': 'Owner Equity', 'type': 'EQUITY', 'tax_rate': tax_exempt, 'ytd': 20000.00},
            {'code': '3100', 'name': 'Retained Earnings', 'type': 'EQUITY', 'tax_rate': tax_exempt, 'ytd': 5000.00},
            
            # Revenue
            {'code': '4000', 'name': 'Sales Revenue', 'type': 'REVENUE', 'tax_rate': standard_rate, 'ytd': 50000.00},
            {'code': '4100', 'name': 'Service Revenue', 'type': 'REVENUE', 'tax_rate': standard_rate, 'ytd': 25000.00},
            
            # Expenses
            {'code': '5000', 'name': 'Cost of Goods Sold', 'type': 'EXPENSE', 'tax_rate': tax_exempt, 'ytd': 20000.00},
            {'code': '5100', 'name': 'Office Supplies', 'type': 'EXPENSE', 'tax_rate': standard_rate, 'ytd': 2000.00},
            {'code': '5200', 'name': 'Rent Expense', 'type': 'EXPENSE', 'tax_rate': tax_exempt, 'ytd': 12000.00},
        ]
        
        for account_data in sample_accounts:
            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults={
                    'name': account_data['name'],
                    'account_type': account_data['type'],
                    'tax_rate': account_data['tax_rate'],
                    'ytd_balance': account_data['ytd'],
                    'is_active': True,
                    'is_locked': False,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created account: {account.code} - {account.name} '
                        f'(${account.ytd_balance:,.2f})'
                    )
                )
            else:
                self.stdout.write(f'→ Account already exists: {account.code} - {account.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 COA setup completed!\n'
                f'- Tax rates created/verified\n'
                f'- Sample accounts created\n'
                f'- Ready to use in Django Admin!'
            )
        )
