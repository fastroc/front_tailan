from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Show admin panel locations for bank account data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== BANK ACCOUNTS IN DJANGO ADMIN ===\n'))
        
        self.stdout.write("🏦 BANK ACCOUNTS DATA LOCATIONS IN ADMIN:\n")
        
        self.stdout.write("1️⃣ PRIMARY LOCATION - COA Accounts:")
        self.stdout.write("   URL: http://localhost:8000/admin/coa/account/")
        self.stdout.write("   Filter by Bank: http://localhost:8000/admin/coa/account/?account_type=Bank")
        self.stdout.write("   📋 Contains: All bank accounts (stored as COA accounts with type='Bank')")
        self.stdout.write("   ✅ Shows: Name, Code, Company, Balance, Status")
        self.stdout.write("")
        
        self.stdout.write("2️⃣ TRANSACTIONS - Bank Transactions:")
        self.stdout.write("   URL: http://localhost:8000/admin/bank_accounts/banktransaction/")
        self.stdout.write("   📋 Contains: All bank transaction records")
        self.stdout.write("   ✅ Shows: Date, Account, Amount, Description, Uploaded By")
        self.stdout.write("")
        
        self.stdout.write("3️⃣ RELATED DATA - Companies:")
        self.stdout.write("   URL: http://localhost:8000/admin/company/company/")
        self.stdout.write("   📋 Contains: All companies that own bank accounts")
        self.stdout.write("   ✅ Shows: Company details, ownership, settings")
        self.stdout.write("")
        
        self.stdout.write("4️⃣ USER MANAGEMENT - Users:")
        self.stdout.write("   URL: http://localhost:8000/admin/auth/user/")
        self.stdout.write("   📋 Contains: All users who can access bank accounts")
        self.stdout.write("   ✅ Shows: User permissions, company access")
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("📍 IMPORTANT NOTES:"))
        self.stdout.write("• Bank accounts are NOT stored in a separate 'bank_accounts' table")
        self.stdout.write("• They are stored in the COA (Chart of Accounts) table with account_type='Bank'")
        self.stdout.write("• To see bank accounts, go to: COA > Accounts > Filter by 'Bank' type")
        self.stdout.write("• Current bank account: 'KhanBank' (Code: 10010, Company: BigBoss)")
        
        self.stdout.write(self.style.SUCCESS('\n=== END ADMIN GUIDE ==='))
