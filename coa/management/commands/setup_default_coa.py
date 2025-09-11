"""
Management command to create default tax rates and sample accounts for companies.
"""
from django.core.management.base import BaseCommand
from company.models import Company
from coa.models import TaxRate, Account, AccountType


class Command(BaseCommand):
    help = 'Create default COA data for all companies'

    def handle(self, *args, **options):
        """Create default tax rates and accounts for each company."""
        companies = Company.objects.all()
        
        if not companies.exists():
            self.stdout.write(
                self.style.ERROR('No companies found. Please create companies first.')
            )
            return
        
        for company in companies:
            self.stdout.write(f'Setting up COA data for: {company.name}')
            
            # Create default tax rates for this company
            tax_rates_data = [
                {'name': 'No Tax', 'rate': 0.0000, 'description': 'No tax applied'},
                {'name': 'GST/HST 5%', 'rate': 0.0500, 'description': 'Goods and Services Tax 5%'},
                {'name': 'GST/HST 13%', 'rate': 0.1300, 'description': 'Harmonized Sales Tax 13%'},
                {'name': 'GST/HST 15%', 'rate': 0.1500, 'description': 'Harmonized Sales Tax 15%'},
                {'name': 'PST 7%', 'rate': 0.0700, 'description': 'Provincial Sales Tax 7%'},
                {'name': 'PST 8%', 'rate': 0.0800, 'description': 'Provincial Sales Tax 8%'},
            ]
            
            created_tax_rates = {}
            for tax_data in tax_rates_data:
                tax_rate, created = TaxRate.objects.get_or_create(
                    company=company,
                    name=tax_data['name'],
                    defaults={
                        'rate': tax_data['rate'],
                        'description': tax_data['description'],
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'  Created tax rate: {tax_rate.name}')
                created_tax_rates[tax_data['name']] = tax_rate
            
            # Get default tax rate (No Tax)
            default_tax = created_tax_rates.get('No Tax')
            if not default_tax:
                default_tax = TaxRate.objects.filter(company=company).first()
            
            if not default_tax:
                self.stdout.write(
                    self.style.ERROR(f'No tax rates found for {company.name}. Skipping accounts creation.')
                )
                continue
            
            # Create sample chart of accounts
            accounts_data = [
                # ASSETS
                {'code': '1000', 'name': 'Cash', 'type': AccountType.CURRENT_ASSET},
                {'code': '1100', 'name': 'Accounts Receivable', 'type': AccountType.CURRENT_ASSET},
                {'code': '1200', 'name': 'Inventory', 'type': AccountType.INVENTORY},
                {'code': '1500', 'name': 'Equipment', 'type': AccountType.FIXED_ASSET},
                {'code': '1600', 'name': 'Accumulated Depreciation - Equipment', 'type': AccountType.FIXED_ASSET},
                
                # LIABILITIES  
                {'code': '2000', 'name': 'Accounts Payable', 'type': AccountType.CURRENT_LIABILITY},
                {'code': '2100', 'name': 'GST/HST Payable', 'type': AccountType.CURRENT_LIABILITY},
                {'code': '2200', 'name': 'Payroll Liabilities', 'type': AccountType.CURRENT_LIABILITY},
                
                # EQUITY
                {'code': '3000', 'name': 'Owner Equity', 'type': AccountType.EQUITY},
                {'code': '3100', 'name': 'Retained Earnings', 'type': AccountType.EQUITY},
                
                # REVENUE
                {'code': '4000', 'name': 'Sales Revenue', 'type': AccountType.SALES},
                {'code': '4100', 'name': 'Service Revenue', 'type': AccountType.REVENUE},
                {'code': '4900', 'name': 'Other Income', 'type': AccountType.OTHER_INCOME},
                
                # EXPENSES
                {'code': '5000', 'name': 'Cost of Goods Sold', 'type': AccountType.DIRECT_COST},
                {'code': '6000', 'name': 'Office Expenses', 'type': AccountType.EXPENSE},
                {'code': '6100', 'name': 'Rent Expense', 'type': AccountType.EXPENSE},
                {'code': '6200', 'name': 'Utilities Expense', 'type': AccountType.EXPENSE},
                {'code': '6300', 'name': 'Insurance Expense', 'type': AccountType.EXPENSE},
                {'code': '6400', 'name': 'Depreciation Expense', 'type': AccountType.DEPRECIATION},
            ]
            
            for account_data in accounts_data:
                account, created = Account.objects.get_or_create(
                    company=company,
                    code=account_data['code'],
                    defaults={
                        'name': account_data['name'],
                        'account_type': account_data['type'],
                        'tax_rate': default_tax,
                        'description': f"Default {account_data['name']} account",
                        'ytd_balance': 0.00,
                        'is_active': True,
                        'is_locked': False,
                    }
                )
                if created:
                    self.stdout.write(f'  Created account: {account.code} - {account.name}')
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ COA setup complete for {company.name}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 Default COA data created for all companies!')
        )
