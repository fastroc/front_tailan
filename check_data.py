#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from bank_accounts.models import UploadedFile, BankTransaction
from coa.models import Account
from company.models import Company

print("=== UPLOADED FILES ===")
files = UploadedFile.objects.all()
for f in files:
    account_name = f.account.name if f.account else "No Account"
    print(f"File ID: {f.id}, Account: {account_name}")
    print(f"  - Original filename: {f.original_filename}")
    print(f"  - Imported count: {f.imported_count}")
    print(f"  - Uploaded: {f.uploaded_at}")

print("\n=== BANK ACCOUNTS ===")
bank_accounts = Account.objects.filter(account_type='Bank')
for account in bank_accounts:
    file_count = UploadedFile.objects.filter(account=account).count()
    transaction_count = BankTransaction.objects.filter(coa_account=account).count()
    print(f"Account: {account.name} (ID: {account.id})")
    print(f"  - Uploaded Files: {file_count}")
    print(f"  - Transactions: {transaction_count}")
    print(f"  - Company: {account.company.name}")

print("\n=== COMPANY FILTER TEST ===")
# Check what company is being used in reconciliation
company = Company.objects.first()
if company:
    print(f"First company: {company.name} (ID: {company.id})")
    accounts_for_company = Account.objects.filter(company=company, account_type='Bank')
    print(f"Bank accounts for {company.name}: {accounts_for_company.count()}")
    for acc in accounts_for_company:
        files = UploadedFile.objects.filter(account=acc)
        print(f"  - {acc.name}: {files.count()} files")
