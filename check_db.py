#!/usr/bin/env python
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from bank_accounts.models import BankTransaction, UploadedFile
from coa.models import Account

print('=== CHECKING DATABASE STATE ===')
print()

# Check all bank accounts
accounts = Account.objects.filter(account_type='Bank')
for acc in accounts:
    print(f'Account: {acc.name} (ID: {acc.id})')
    print(f'  Current Balance: ${acc.current_balance}')
    
    # Check transactions
    transactions = BankTransaction.objects.filter(coa_account=acc)
    print(f'  Transactions count: {transactions.count()}')
    if transactions.count() > 0:
        total = sum(t.amount for t in transactions)
        print(f'  Actual total from transactions: ${total}')
        print(f'  Sample transactions:')
        for t in transactions[:5]:
            print(f'    - {t.date}: ${t.amount} (file: {t.uploaded_file})')
    
    # Check uploaded files
    uploads = UploadedFile.objects.filter(account=acc)
    print(f'  Upload records: {uploads.count()}')
    for upload in uploads:
        print(f'    - {upload.original_filename} ({upload.imported_count} transactions)')
    print()

print('=== ORPHANED TRANSACTIONS CHECK ===')
# Check for transactions without corresponding upload files
all_transactions = BankTransaction.objects.all()
print(f'Total transactions in database: {all_transactions.count()}')

orphaned = []
for t in all_transactions:
    # Check if this transaction's upload file still exists
    upload_exists = UploadedFile.objects.filter(
        stored_filename=t.uploaded_file,
        account=t.coa_account
    ).exists()
    if not upload_exists:
        orphaned.append(t)

print(f'Orphaned transactions (no matching upload record): {len(orphaned)}')
if orphaned:
    print('Sample orphaned transactions:')
    for t in orphaned[:5]:
        print(f'  - {t.date}: ${t.amount} (file: {t.uploaded_file}) - Account: {t.coa_account.name}')
