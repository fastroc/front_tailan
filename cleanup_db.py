#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from bank_accounts.models import BankTransaction, UploadedFile
from coa.models import Account

print('=== CLEANING UP ORPHANED TRANSACTIONS ===')
print()

# Find all orphaned transactions (transactions without corresponding upload records)
all_transactions = BankTransaction.objects.all()
orphaned_count = 0

for transaction in all_transactions:
    # Check if this transaction's upload file still exists
    upload_exists = UploadedFile.objects.filter(
        stored_filename=transaction.uploaded_file,
        account=transaction.coa_account
    ).exists()
    
    # Also check for transactions with empty uploaded_file field
    if not upload_exists or not transaction.uploaded_file:
        print(f'Deleting orphaned transaction: {transaction.date} ${transaction.amount} (file: "{transaction.uploaded_file}")')
        transaction.delete()
        orphaned_count += 1

print(f'\n✅ Deleted {orphaned_count} orphaned transactions')

# Recalculate all account balances
print('\n=== RECALCULATING ACCOUNT BALANCES ===')
accounts = Account.objects.filter(account_type='Bank')
for account in accounts:
    transactions = BankTransaction.objects.filter(coa_account=account)
    new_balance = sum(t.amount for t in transactions)
    old_balance = account.current_balance
    
    account.current_balance = new_balance
    account.save()
    
    print(f'Account: {account.name}')
    print(f'  Old balance: ${old_balance}')
    print(f'  New balance: ${new_balance}')
    print(f'  Remaining transactions: {transactions.count()}')
    print()

print('✅ Database cleanup completed!')
