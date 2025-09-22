"""
Django management command to create financial rules demo data
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from financial_rules.models import BaseFinancialRule, RuleCondition, RuleAction
from company.models import Company


class Command(BaseCommand):
    help = 'Create demo data for financial rules system'

    def handle(self, *args, **options):
        self.stdout.write("Creating Financial Rules Demo Data...")
        
        try:
            with transaction.atomic():
                # Create demo companies if they don't exist
                companies = self.create_demo_companies()
                
                # Create rules
                self.create_loan_payment_rules(companies)
                self.create_contact_based_rules(companies)
                self.create_general_rules(companies)
                
                # Print summary
                self.print_summary()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating demo data: {e}')
            )
            raise

    def create_demo_companies(self):
        """Use existing companies or create demo companies if none exist"""
        companies = []
        
        # First try to use existing companies
        existing_companies = Company.objects.all()[:3]
        if existing_companies.count() >= 1:
            self.stdout.write("Using existing companies:")
            for company in existing_companies:
                companies.append(company)
                self.stdout.write(f"- Using company: {company.name}")
            return companies
        
        # If no existing companies, we need to get a user to be the owner
        from django.contrib.auth.models import User
        try:
            # Try to get the first user as owner
            owner = User.objects.first()
            if not owner:
                self.stdout.write("⚠️ No users found. Creating a demo user...")
                owner = User.objects.create_user(
                    username='demo_user',
                    email='demo@example.com',
                    password='demo123',
                    first_name='Demo',
                    last_name='User'
                )
                self.stdout.write(f"✅ Created demo user: {owner.username}")
        except Exception as e:
            self.stdout.write(f"❌ Error creating demo user: {e}")
            return []
        
        company_data = [
            {'name': 'TechCorp Solutions', 'description': 'Technology consulting company'},
            {'name': 'BuildRight Construction', 'description': 'General construction and contracting'},
            {'name': 'Green Energy LLC', 'description': 'Renewable energy solutions'}
        ]
        
        for data in company_data:
            try:
                company, created = Company.objects.get_or_create(
                    name=data['name'],
                    defaults={
                        **data,
                        'owner': owner,
                        'currency': 'USD',
                        'country': 'United States'
                    }
                )
                companies.append(company)
                if created:
                    self.stdout.write(f"✅ Created company: {company.name}")
                else:
                    self.stdout.write(f"- Company exists: {company.name}")
            except Exception as e:
                self.stdout.write(f"❌ Error creating company {data['name']}: {e}")
        
        return companies

    def create_loan_payment_rules(self, companies):
        """Create sample loan payment rules"""
        self.stdout.write("\n=== Creating Loan Payment Rules ===")
        
        for company in companies:
            rule, created = BaseFinancialRule.objects.get_or_create(
                name=f"{company.name} - Loan Payment Processing",
                company=company,
                defaults={
                    'description': f'Automatically split loan payments for {company.name}',
                    'rule_type': 'loan_payment',
                    'priority': 1,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f"✓ Created rule: {rule.name}")
                
                # Add conditions
                RuleCondition.objects.create(
                    rule=rule,
                    field_name='transaction_description',
                    operator='contains',
                    value='loan payment',
                    is_case_sensitive=False
                )
                
                RuleCondition.objects.create(
                    rule=rule,
                    field_name='transaction_amount',
                    operator='gte',
                    value='100.00'
                )
                
                # Add actions
                RuleAction.objects.create(
                    rule=rule,
                    sequence=1,
                    description_template='Late Fees - {customer_name}',
                    account_code='2100',
                    allocation_type='percentage',
                    value=Decimal('10.00')
                )
                
                RuleAction.objects.create(
                    rule=rule,
                    sequence=2,
                    description_template='Interest Payment - {customer_name}',
                    account_code='2200',
                    allocation_type='percentage',
                    value=Decimal('30.00')
                )
                
                RuleAction.objects.create(
                    rule=rule,
                    sequence=3,
                    description_template='Principal Payment - {customer_name}',
                    account_code='2000',
                    allocation_type='remainder',
                    value=Decimal('0.00')
                )
            else:
                self.stdout.write(f"- Rule exists: {rule.name}")

    def create_contact_based_rules(self, companies):
        """Create sample contact-based rules"""
        self.stdout.write("\n=== Creating Contact-Based Rules ===")
        
        vendor_rules = [
            {
                'name': 'BigBoss LLC Payments',
                'contact_patterns': ['bigboss', 'big boss'],
                'account': '2500'
            },
            {
                'name': 'Office Supply Vendors',
                'contact_patterns': ['officemax', 'staples'],
                'account': '6100'
            }
        ]
        
        for company in companies:
            for vendor_data in vendor_rules:
                rule, created = BaseFinancialRule.objects.get_or_create(
                    name=f"{company.name} - {vendor_data['name']}",
                    company=company,
                    defaults={
                        'description': f"Payments to {vendor_data['name']}",
                        'rule_type': 'contact_based',
                        'priority': 15,
                        'is_active': True
                    }
                )
                
                if created:
                    self.stdout.write(f"✓ Created rule: {rule.name}")
                    
                    # Add contact conditions
                    for i, pattern in enumerate(vendor_data['contact_patterns']):
                        RuleCondition.objects.create(
                            rule=rule,
                            field_name='customer_name',
                            operator='contains',
                            value=pattern,
                            is_case_sensitive=False
                        )
                    
                    # Add action
                    RuleAction.objects.create(
                        rule=rule,
                        sequence=1,
                        description_template=f'Payment to {vendor_data["name"]} - {{customer_name}}',
                        account_code=vendor_data['account'],
                        allocation_type='percentage',
                        value=Decimal('100.00')
                    )

    def create_general_rules(self, companies):
        """Create sample general rules"""
        self.stdout.write("\n=== Creating General Rules ===")
        
        for company in companies:
            rule, created = BaseFinancialRule.objects.get_or_create(
                name=f"{company.name} - Small Cash Transactions",
                company=company,
                defaults={
                    'description': 'Categorize small cash transactions as petty cash',
                    'rule_type': 'amount_based',
                    'priority': 20,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f"✓ Created rule: {rule.name}")
                
                RuleCondition.objects.create(
                    rule=rule,
                    field_name='transaction_amount',
                    operator='lte',
                    value='50.00'
                )
                
                RuleCondition.objects.create(
                    rule=rule,
                    field_name='transaction_description',
                    operator='contains',
                    value='cash',
                    is_case_sensitive=False
                )
                
                RuleAction.objects.create(
                    rule=rule,
                    sequence=1,
                    description_template='Petty Cash - {transaction_description}',
                    account_code='1200',
                    allocation_type='percentage',
                    value=Decimal('100.00')
                )

    def print_summary(self):
        """Print summary of created rules"""
        total_rules = BaseFinancialRule.objects.count()
        active_rules = BaseFinancialRule.objects.filter(is_active=True).count()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("DEMO DATA CREATION COMPLETE")
        self.stdout.write("="*50)
        self.stdout.write(f"Total Rules: {total_rules}")
        self.stdout.write(f"Active Rules: {active_rules}")
        self.stdout.write("\nAccess the system at: http://localhost:8000/financial_rules/test/")
        self.stdout.write("="*50)
