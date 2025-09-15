#!/usr/bin/env python
import os
import sys
import django
import csv
from datetime import datetime
from decimal import Decimal

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from bank_accounts.models import BankTransaction, UploadedFile
from coa.models import Account
from django.contrib.auth.models import User

def upload_csv_to_account(csv_file_path, account_id, account_name):
    """Upload CSV transactions to specific account"""
    print(f"\n=== Uploading {csv_file_path} to {account_name} ===")
    
    # Get account
    account = Account.objects.get(id=account_id)
    
    # Get first user (for uploaded_by field)
    user = User.objects.first()
    
    # Read CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        # Auto-detect delimiter
        first_line = file.readline()
        file.seek(0)
        delimiter = ';' if ';' in first_line and first_line.count(';') > first_line.count(',') else ','
        
        csv_reader = csv.DictReader(file, delimiter=delimiter)
        
        transactions_created = 0
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Parse date (supports multiple formats)
                date_str = row['Date'].strip()
                try:
                    transaction_date = datetime.strptime(date_str, '%Y.%m.%d').date()
                except ValueError:
                    try:
                        transaction_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    except ValueError:
                        transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                
                # Parse amount
                amount_str = row['Amount'].strip().replace(',', '')
                amount = Decimal(amount_str)
                
                # Get other fields
                description = row['Description'].strip()
                reference = row['Reference'].strip()
                
                # Create transaction
                transaction = BankTransaction.objects.create(
                    coa_account=account,
                    date=transaction_date,
                    amount=amount,
                    description=description,
                    reference=reference,
                    uploaded_file=os.path.basename(csv_file_path),
                    uploaded_by=user
                )
                
                transactions_created += 1
                print(f"  Row {row_num}: {date_str} | {description[:30]} | {amount}")
                
            except Exception as e:
                print(f"  ERROR Row {row_num}: {str(e)}")
                continue
    
    print(f"✅ Created {transactions_created} transactions for {account_name}")
    return transactions_created

# Main upload process
print("=== Automated CSV Upload Process ===")

# Upload operating account to KhanBank
khan_count = upload_csv_to_account(
    'files/bank_transactions_operating_q1_2025.csv',
    155,  # KhanBank ID
    'KhanBank (Operating)'
)

# Upload payroll account to Golomt
golomt_count = upload_csv_to_account(
    'files/bank_transactions_payroll_q1_2025.csv', 
    156,  # Golomt ID
    'Golomt (Payroll)'
)

print(f"\n=== Upload Summary ===")
print(f"KhanBank: {khan_count} transactions")
print(f"Golomt: {golomt_count} transactions")
print(f"Total: {khan_count + golomt_count} transactions")

# Verify balances
from django.db.models import Sum
khan_account = Account.objects.get(id=155)
golomt_account = Account.objects.get(id=156)

khan_balance = BankTransaction.objects.filter(coa_account=khan_account).aggregate(Sum('amount'))['amount__sum'] or 0
golomt_balance = BankTransaction.objects.filter(coa_account=golomt_account).aggregate(Sum('amount'))['amount__sum'] or 0

print(f"\n=== Account Balances ===")
print(f"KhanBank Balance: ${khan_balance:,.2f}")
print(f"Golomt Balance: ${golomt_balance:,.2f}")
print("\n✅ Upload completed successfully!")
