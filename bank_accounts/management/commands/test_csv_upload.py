from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from coa.models import Account
from bank_accounts.models import BankTransaction
import csv
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = 'Test CSV upload processing with sample bank statement'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== TESTING CSV UPLOAD PROCESSING ===\n'))
        
        # Get the bank account
        try:
            account = Account.objects.get(id=86, account_type='Bank')
            self.stdout.write(f"✅ Found bank account: {account.name} (ID: {account.id})")
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Bank account with ID 86 not found"))
            return
        
        # Get a user for uploaded_by
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No users found"))
            return
        
        # Test CSV processing
        csv_file_path = os.path.join('files', 'BankStatement_XeroStrict.csv')
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"❌ CSV file not found: {csv_file_path}"))
            return
        
        self.stdout.write(f"📂 Processing CSV file: {csv_file_path}")
        
        transactions_created = 0
        errors = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_data = csv.DictReader(file)
                
                # Show first few rows for validation
                self.stdout.write("📋 Sample data preview:")
                sample_rows = []
                for i, row in enumerate(csv_data):
                    if i < 3:  # Show first 3 rows
                        sample_rows.append(row)
                    if i >= 5:  # Process only first 5 rows for testing
                        break
                
                # Reset file pointer
                file.seek(0)
                csv_data = csv.DictReader(file)
                
                for row_num, row in enumerate(csv_data, start=2):
                    if row_num > 6:  # Process only first 5 transactions for testing
                        break
                        
                    try:
                        # Parse date
                        date_str = row['Date'].strip()
                        try:
                            transaction_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        except ValueError:
                            try:
                                transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                            except ValueError:
                                errors.append(f"Row {row_num}: Invalid date format '{date_str}'")
                                continue
                        
                        # Parse amount
                        amount_str = row['Amount'].strip().replace(',', '')
                        try:
                            amount = Decimal(amount_str)
                        except (ValueError, InvalidOperation):
                            errors.append(f"Row {row_num}: Invalid amount '{amount_str}'")
                            continue
                        
                        # Get other fields
                        description = row['Description'].strip()
                        reference = row['Reference'].strip()
                        
                        self.stdout.write(f"  📝 Row {row_num-1}: {transaction_date} | ${amount} | {description}")
                        
                        # Would create transaction here in real upload
                        # BankTransaction.objects.create(...)
                        transactions_created += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                
                self.stdout.write(f"\n✅ Successfully processed {transactions_created} transactions!")
                
                if errors:
                    self.stdout.write(f"\n⚠️ {len(errors)} errors found:")
                    for error in errors:
                        self.stdout.write(f"  {error}")
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error processing CSV: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS('\n=== END CSV TEST ==='))
