from django.core.management.base import BaseCommand
from django.db import connection
from coa.models import Account
from bank_accounts.models import BankTransaction


class Command(BaseCommand):
    help = 'Show detailed database table contents for bank accounts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== DATABASE TABLES ANALYSIS ===\n'))
        
        # Show COA Account table structure and data
        self.stdout.write("🗄️ COA_ACCOUNT Table (Bank accounts stored here):")
        bank_accounts = Account.objects.filter(account_type='Bank').select_related('company', 'created_by')
        
        if bank_accounts.exists():
            for account in bank_accounts:
                self.stdout.write(f"  📋 Account ID: {account.id}")
                self.stdout.write(f"     Name: {account.name}")
                self.stdout.write(f"     Code: {account.code or 'NULL'}")
                self.stdout.write(f"     Type: {account.account_type}")
                self.stdout.write(f"     Company: {account.company.name} (ID: {account.company.id})")
                self.stdout.write(f"     Current Balance: ${account.current_balance or 0}")
                self.stdout.write(f"     Opening Balance: ${account.opening_balance or 0}")
                self.stdout.write(f"     YTD Balance: ${account.ytd_balance or 0}")
                self.stdout.write(f"     Created By: {account.created_by.username if account.created_by else 'NULL'}")
                self.stdout.write(f"     Created At: {account.created_at}")
                self.stdout.write(f"     Is Active: {account.is_active}")
                self.stdout.write(f"     Is Essential: {account.is_essential}")
                self.stdout.write("")
        else:
            self.stdout.write("  ❌ No bank accounts found")
        
        # Show Bank Transactions table
        self.stdout.write("💳 BANK_TRANSACTIONS Table:")
        transactions = BankTransaction.objects.all().select_related('coa_account', 'uploaded_by')
        
        if transactions.exists():
            for transaction in transactions:
                self.stdout.write(f"  📋 Transaction ID: {transaction.id}")
                self.stdout.write(f"     Date: {transaction.date}")
                self.stdout.write(f"     Account: {transaction.coa_account.name}")
                self.stdout.write(f"     Description: {transaction.description}")
                self.stdout.write(f"     Amount: ${transaction.amount}")
                self.stdout.write(f"     Reference: {transaction.reference}")
                self.stdout.write(f"     Uploaded By: {transaction.uploaded_by.username}")
                self.stdout.write(f"     Uploaded At: {transaction.uploaded_at}")
                self.stdout.write("")
        else:
            self.stdout.write("  ❌ No bank transactions found")
        
        # Show raw SQL query results
        self.stdout.write("🔍 Raw SQL Results:")
        with connection.cursor() as cursor:
            # Check bank accounts
            cursor.execute("""
                SELECT a.id, a.name, a.code, a.account_type, a.current_balance, 
                       c.name as company_name, u.username as created_by
                FROM coa_account a 
                LEFT JOIN company_company c ON a.company_id = c.id
                LEFT JOIN auth_user u ON a.created_by_id = u.id
                WHERE a.account_type = 'Bank'
            """)
            
            rows = cursor.fetchall()
            if rows:
                self.stdout.write("  Bank Accounts (Raw SQL):")
                for row in rows:
                    self.stdout.write(f"    {row}")
            else:
                self.stdout.write("  No bank accounts in raw SQL")
        
        self.stdout.write(self.style.SUCCESS('\n=== END DATABASE ANALYSIS ==='))
