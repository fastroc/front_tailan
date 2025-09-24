from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from coa.models import Account
from bank_accounts.models import BankTransaction
from company.models import Company
import csv
import os
from datetime import datetime
from decimal import Decimal


class Command(BaseCommand):
    help = 'Import loan payment transactions from CSV file'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== IMPORTING LOAN PAYMENT TRANSACTIONS ===\n'))
        
        # Get or create company
        company = Company.objects.first()
        if not company:
            self.stdout.write(self.style.ERROR("❌ No companies found"))
            return
        
        # Get or create a bank account for loan payments
        loan_payments_account, created = Account.objects.get_or_create(
            code='1250',
            company=company,
            defaults={
                'name': 'Loan Payments Received',
                'account_type': 'current_asset',
                'description': 'Staging account for loan payments received'
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created account: {loan_payments_account.name} (ID: {loan_payments_account.id})")
        else:
            self.stdout.write(f"✅ Using existing account: {loan_payments_account.name} (ID: {loan_payments_account.id})")
        
        # Get a user for uploaded_by
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No users found"))
            return
        
        # Process loan payments CSV
        csv_file_path = 'bank_transactions_q1_2025_loan_payments.csv'
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"❌ CSV file not found: {csv_file_path}"))
            return
        
        self.stdout.write(f"📂 Processing CSV file: {csv_file_path}")
        
        transactions_created = 0
        errors = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_data = csv.DictReader(file)
                
                for row_num, row in enumerate(csv_data, start=2):
                    try:
                        # Parse date - expecting YYYY-MM-DD format from the CSV
                        date_str = row['date'].strip()
                        transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # Parse amount
                        amount_str = row['amount'].strip().replace(',', '')
                        amount = Decimal(amount_str)
                        
                        # Get other fields
                        description = row['description'].strip()
                        customer_name = row['customer_name'].strip()
                        reference = row['reference_number'].strip()
                        
                        # Create description that includes customer name for loan detection
                        full_description = f"{description} - {customer_name}"
                        
                        # Check if transaction already exists (duplicate prevention)
                        existing = BankTransaction.objects.filter(
                            coa_account=loan_payments_account,
                            date=transaction_date,
                            amount=amount,
                            reference=reference
                        ).first()
                        
                        if existing:
                            self.stdout.write(f"  ⚠️ Skipping duplicate: {transaction_date} | ${amount} | {customer_name}")
                            continue
                        
                        # Create transaction
                        transaction = BankTransaction.objects.create(
                            coa_account=loan_payments_account,
                            company=company,
                            date=transaction_date,
                            amount=amount,
                            description=full_description,
                            reference=reference,
                            uploaded_by=user
                        )
                        
                        transactions_created += 1
                        self.stdout.write(f"  ✅ Created: {transaction_date} | ${amount} | {customer_name}")
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                
                self.stdout.write(f"\n🎉 Successfully imported {transactions_created} loan payment transactions!")
                
                if errors:
                    self.stdout.write(f"\n⚠️ {len(errors)} errors found:")
                    for error in errors:
                        self.stdout.write(f"  {error}")
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error processing CSV: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS('\n=== IMPORT COMPLETE ==='))
        self.stdout.write(f"💡 You can now access loan payments at: http://localhost:8000/reconciliation/account/{loan_payments_account.id}/")
