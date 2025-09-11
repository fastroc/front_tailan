#!/usr/bin/env python
"""Check bank account balances for reconciliation system"""

import os
import sys
import django

# Add the project path
sys.path.append(r'D:\Again')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from bank_accounts.models import BankTransaction
from coa.models import Account
from django.db.models import Sum

def check_balances():
    print("=== Bank Account Balance Check ===\n")
    
    # Get all bank accounts
    bank_accounts = Account.objects.filter(account_type='Bank')
    
    for account in bank_accounts:
        transactions = BankTransaction.objects.filter(coa_account=account)
        count = transactions.count()
        balance_result = transactions.aggregate(total=Sum('amount'))
        balance = balance_result['total'] or 0
        
        print(f"Account: {account.name}")
        print(f"  - Transactions: {count}")
        print(f"  - Total Balance: ${balance:.2f}")
        print(f"  - Account ID: {account.id}")
        print()

if __name__ == "__main__":
    check_balances()
