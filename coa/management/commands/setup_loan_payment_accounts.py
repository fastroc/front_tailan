"""
Management command to set up loan payment GL accounts for proper accounting flow
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from coa.models import Account, AccountType
from company.models import Company


class Command(BaseCommand):
    help = 'Set up loan payment GL accounts for all companies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Set up accounts for specific company ID only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating accounts'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🏦 Setting up Loan Payment GL Accounts...")
        
        # Determine which companies to process
        if options.get('company_id'):
            companies = Company.objects.filter(id=options['company_id'])
            if not companies.exists():
                self.stderr.write(f"Company with ID {options['company_id']} not found")
                return
        else:
            companies = Company.objects.all()
        
        self.stdout.write(f"Processing {companies.count()} companies...")
        
        for company in companies:
            self.stdout.write(f"\n📊 Company: {company.name} (ID: {company.id})")
            self.setup_loan_accounts_for_company(company, options.get('dry_run', False))
        
        self.stdout.write("\n✅ Loan payment GL account setup completed!")
    
    def setup_loan_accounts_for_company(self, company, dry_run=False):
        """Set up loan payment accounts for a specific company"""
        
        # Define the accounts we need
        accounts_to_create = [
            {
                'code': '1250',
                'name': 'Loan Payments Received',
                'account_type': 'asset',
                'description': 'Staging account for incoming loan payments before allocation'
            },
            {
                'code': '1251', 
                'name': 'Loan Payment Clearing',
                'account_type': 'asset',
                'description': 'Clearing account for loan payment processing'
            }
        ]
        
        # Get or create appropriate account type
        asset_type, created = AccountType.objects.get_or_create(
            name='Current Assets',
            defaults={
                'category': 'asset',
                'normal_balance': 'debit'
            }
        )
        
        if created and not dry_run:
            self.stdout.write(f"  📁 Created account type: {asset_type.name}")
        
        for account_data in accounts_to_create:
            existing_account = Account.objects.filter(
                company=company,
                code=account_data['code']
            ).first()
            
            if existing_account:
                self.stdout.write(f"  ✅ Account {account_data['code']} already exists: {existing_account.name}")
                continue
            
            if dry_run:
                self.stdout.write(f"  🔍 [DRY RUN] Would create: {account_data['code']} - {account_data['name']}")
                continue
            
            try:
                with transaction.atomic():
                    account = Account.objects.create(
                        company=company,
                        code=account_data['code'],
                        name=account_data['name'],
                        account_type=asset_type,
                        description=account_data['description'],
                        is_active=True
                    )
                    
                    self.stdout.write(f"  ✨ Created: {account.code} - {account.name}")
                    
            except Exception as e:
                self.stderr.write(f"  ❌ Error creating account {account_data['code']}: {str(e)}")
        
        # Check for other loan-related accounts
        existing_loan_accounts = Account.objects.filter(
            company=company,
            name__icontains='loan'
        ).exclude(
            code__in=['1250', '1251']
        ).order_by('code')
        
        if existing_loan_accounts.exists():
            self.stdout.write(f"  📋 Other loan accounts in {company.name}:")
            for account in existing_loan_accounts:
                self.stdout.write(f"    {account.code} - {account.name}")
