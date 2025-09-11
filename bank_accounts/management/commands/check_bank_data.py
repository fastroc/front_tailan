from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from company.models import Company
from coa.models import Account
from bank_accounts.models import BankTransaction


class Command(BaseCommand):
    help = 'Check bank accounts and transaction data in the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== BANK ACCOUNTS DATA ANALYSIS ===\n'))
        
        # Check Companies
        companies = Company.objects.all()
        self.stdout.write(f"📊 Total Companies: {companies.count()}")
        for company in companies:
            self.stdout.write(f"  - {company.name} (ID: {company.id}, Active: {company.is_active})")
        
        # Check Bank Accounts (COA Accounts with type='Bank')
        bank_accounts = Account.objects.filter(account_type='Bank')
        self.stdout.write(f"\n🏦 Total Bank Accounts: {bank_accounts.count()}")
        
        if bank_accounts.exists():
            for account in bank_accounts:
                self.stdout.write(f"  - {account.name}")
                self.stdout.write(f"    Code: {account.code or 'Not set'}")
                self.stdout.write(f"    Company: {account.company.name}")
                self.stdout.write(f"    Balance: ${account.current_balance or 0}")
                self.stdout.write(f"    Created: {account.created_at}")
                self.stdout.write("")
        else:
            self.stdout.write("  No bank accounts found")
        
        # Check Bank Transactions
        transactions = BankTransaction.objects.all()
        self.stdout.write(f"💰 Total Bank Transactions: {transactions.count()}")
        
        if transactions.exists():
            for transaction in transactions[:5]:  # Show first 5
                self.stdout.write(f"  - {transaction.id}: {transaction.account.name}")
                self.stdout.write(f"    User: {transaction.user.username}")
                self.stdout.write(f"    Created: {transaction.created_at}")
        else:
            self.stdout.write("  No bank transactions found")
        
        # Check Users
        users = User.objects.all()
        self.stdout.write(f"\n👥 Total Users: {users.count()}")
        for user in users:
            self.stdout.write(f"  - {user.username} ({user.first_name} {user.last_name})")
        
        self.stdout.write(self.style.SUCCESS('\n=== END ANALYSIS ==='))
