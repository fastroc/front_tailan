#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from bank_accounts.models import BankTransaction
from coa.models import Account

# Check transaction details
golomt = Account.objects.get(id=87)
txn = BankTransaction.objects.filter(coa_account=golomt).first()

print(f"Transaction ID: {txn.id}")
print(f"Date: {txn.date}")
print(f"Amount: {txn.amount} (type: {type(txn.amount)})")
print(f"Description: {txn.description}")
print(f"Raw amount value: {repr(txn.amount)}")
