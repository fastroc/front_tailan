from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from coa.models import Account
from bank_accounts.models import BankTransaction
from company.models import Company
from datetime import date
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create sample loan payment transactions for testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== CREATING SAMPLE LOAN PAYMENT TRANSACTIONS ===\n'))
        
        # Get or create company
        company = Company.objects.first()
        if not company:
            self.stdout.write(self.style.ERROR("❌ No companies found"))
            return
        
        # Try to use account 203 first, or create a loan payments account
        try:
            account = Account.objects.get(id=203, company=company)
            self.stdout.write(f"✅ Using existing account 203: {account.name}")
        except Account.DoesNotExist:
            # Create account 203 or use a similar account
            account = Account.objects.filter(
                company=company,
                account_type__in=['current_asset', 'Bank', 'CURRENT_ASSET', 'bank']
            ).first()
            
            if not account:
                # Create a new account
                account = Account.objects.create(
                    code='1250',
                    name='Loan Payments Received', 
                    company=company,
                    account_type='current_asset',
                    description='Account for receiving loan payments'
                )
                self.stdout.write(f"✅ Created new account: {account.name} (ID: {account.id})")
            else:
                self.stdout.write(f"✅ Using existing account: {account.name} (ID: {account.id})")
        
        # Get a user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No users found"))
            return
        
        # Create sample loan payment transactions
        sample_transactions = [
            {
                'date': date(2025, 3, 5),
                'amount': Decimal('247.78'),
                'customer': 'Richard Rodriguez',
                'description': 'RRodriguez PMT',
                'reference': 'REF568877'
            },
            {
                'date': date(2025, 3, 11), 
                'amount': Decimal('239.39'),
                'customer': 'Joseph Johnson',
                'description': 'Johnson,Joseph PAYMENT',
                'reference': 'REF970729'
            },
            {
                'date': date(2025, 3, 14),
                'amount': Decimal('443.31'),
                'customer': 'David Anderson', 
                'description': 'Anderson MONTHLY PAYMENT',
                'reference': 'REF674748'
            },
            {
                'date': date(2025, 3, 15),
                'amount': Decimal('445.44'),
                'customer': 'David Johnson',
                'description': 'Johnson MONTHLY PAYMENT', 
                'reference': 'REF191741'
            },
            {
                'date': date(2025, 3, 24),
                'amount': Decimal('372.64'),
                'customer': 'Mary Jackson',
                'description': 'LOAN PAYMENT Jackson',
                'reference': 'REF165726'
            }
        ]
        
        transactions_created = 0
        
        for trans_data in sample_transactions:
            # Check if transaction already exists
            existing = BankTransaction.objects.filter(
                coa_account=account,
                date=trans_data['date'],
                amount=trans_data['amount'],
                reference=trans_data['reference']
            ).first()
            
            if existing:
                self.stdout.write(f"  ⚠️ Skipping duplicate: {trans_data['date']} | ${trans_data['amount']} | {trans_data['customer']}")
                continue
            
            # Create transaction with customer name in description for loan detection
            full_description = f"{trans_data['description']} - {trans_data['customer']}"
            
            transaction = BankTransaction.objects.create(
                coa_account=account,
                company=company,
                date=trans_data['date'],
                amount=trans_data['amount'],
                description=full_description,
                reference=trans_data['reference'],
                uploaded_by=user
            )
            
            transactions_created += 1
            self.stdout.write(f"  ✅ Created: {trans_data['date']} | ${trans_data['amount']} | {trans_data['customer']}")
        
        self.stdout.write(f"\n🎉 Successfully created {transactions_created} sample loan payment transactions!")
        self.stdout.write(f"💡 You can now access them at: http://localhost:8000/reconciliation/account/{account.id}/")
        self.stdout.write(f"💡 Account: {account.name} (ID: {account.id})")
        self.stdout.write(self.style.SUCCESS('\n=== SAMPLE DATA CREATION COMPLETE ==='))
