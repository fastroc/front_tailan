from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reconciliation.models import UploadedFile, BankTransaction
from django.utils import timezone
from datetime import date
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample reconciliation data for showcase'

    def handle(self, *args, **options):
        # Get or create a user for demo
        user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User'
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write(f'Created demo user: {user.username}')
        
        # Clear existing sample data
        UploadedFile.objects.filter(uploaded_by=user).delete()
        
        # Create sample uploaded files
        files_data = [
            {
                'file_name': 'january_2025_statement.csv',
                'bank_account_name': 'Business Checking Account',
                'statement_period': 'January 2025',
                'file_size': 2048,
                'is_processed': True,
                'processed_at': timezone.make_aware(timezone.datetime(2025, 1, 15, 10, 30)),
            },
            {
                'file_name': 'december_2024_statement.csv', 
                'bank_account_name': 'Business Savings Account',
                'statement_period': 'December 2024',
                'file_size': 1536,
                'is_processed': True,
                'processed_at': timezone.make_aware(timezone.datetime(2024, 12, 20, 14, 45)),
            },
            {
                'file_name': 'february_2025_statement.csv',
                'bank_account_name': 'Business Checking Account', 
                'statement_period': 'February 2025',
                'file_size': 3072,
                'is_processed': False,
            }
        ]
        
        for file_data in files_data:
            # Create dummy file path since file field is required
            from django.core.files.base import ContentFile
            dummy_content = ContentFile(b"Date,Description,Amount\n")
            dummy_content.name = file_data['file_name']
            
            uploaded_file = UploadedFile.objects.create(
                uploaded_by=user,
                file=dummy_content,
                file_name=file_data['file_name'],
                bank_account_name=file_data['bank_account_name'],
                statement_period=file_data['statement_period'],
                file_size=file_data['file_size'],
                is_processed=file_data['is_processed'],
                processed_at=file_data.get('processed_at'),
            )
            self.stdout.write(f'Created file: {uploaded_file.file_name}')
            
            # Add transactions for processed files
            if uploaded_file.is_processed:
                self.create_transactions(uploaded_file)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample reconciliation data!')
        )

    def create_transactions(self, uploaded_file):
        """Create sample transactions for a file"""
        if 'january' in uploaded_file.file_name.lower():
            transactions_data = [
                {'date': date(2025, 1, 1), 'amount': Decimal('5000.00'), 'payee': 'Opening Balance', 'description': 'Beginning balance for January', 'reference': 'OB001'},
                {'date': date(2025, 1, 2), 'amount': Decimal('-1200.00'), 'payee': 'Downtown Properties LLC', 'description': 'Monthly office rent payment', 'reference': 'RENT001'},
                {'date': date(2025, 1, 3), 'amount': Decimal('2500.00'), 'payee': 'ABC Corporation', 'description': 'Invoice payment received - Project Alpha', 'reference': 'INV2025001'},
                {'date': date(2025, 1, 4), 'amount': Decimal('-89.99'), 'payee': 'Telecom Solutions Inc', 'description': 'Monthly internet and phone service', 'reference': 'UTIL001'},
                {'date': date(2025, 1, 5), 'amount': Decimal('-245.50'), 'payee': 'Office Supply World', 'description': 'Printer paper, toner, office supplies', 'reference': 'SUPP001'},
                {'date': date(2025, 1, 6), 'amount': Decimal('1800.00'), 'payee': 'XYZ Consulting Ltd', 'description': 'Consulting services rendered', 'reference': 'CONS001'},
                {'date': date(2025, 1, 7), 'amount': Decimal('-25.00'), 'payee': 'First National Bank', 'description': 'Monthly service fee', 'reference': 'FEE001'},
                {'date': date(2025, 1, 8), 'amount': Decimal('-3200.00'), 'payee': 'Payroll Services Inc', 'description': 'Employee payroll - January 1st half', 'reference': 'PAY001'},
                {'date': date(2025, 1, 9), 'amount': Decimal('-150.00'), 'payee': 'Digital Marketing Co', 'description': 'Google Ads campaign spending', 'reference': 'MKTG001'},
                {'date': date(2025, 1, 10), 'amount': Decimal('-300.00'), 'payee': 'Johnson & Associates', 'description': 'Customer refund processed', 'reference': 'REF001'},
                {'date': date(2025, 1, 12), 'amount': Decimal('3750.00'), 'payee': 'Global Tech Solutions', 'description': 'Project milestone payment', 'reference': 'PROJ001'},
                {'date': date(2025, 1, 15), 'amount': Decimal('-2800.00'), 'payee': 'Payroll Services Inc', 'description': 'Employee payroll - January 2nd half', 'reference': 'PAY002'},
                {'date': date(2025, 1, 18), 'amount': Decimal('1200.00'), 'payee': 'Regional Partners LLC', 'description': 'Service contract payment', 'reference': 'SVC001'},
                {'date': date(2025, 1, 22), 'amount': Decimal('-450.00'), 'payee': 'Legal Advisory Group', 'description': 'Legal consultation fees', 'reference': 'LEGAL001'},
                {'date': date(2025, 1, 25), 'amount': Decimal('950.00'), 'payee': 'Metro Business Center', 'description': 'Conference room rental income', 'reference': 'RENT002'},
            ]
        elif 'december' in uploaded_file.file_name.lower():
            transactions_data = [
                {'date': date(2024, 12, 1), 'amount': Decimal('4200.00'), 'payee': 'Opening Balance', 'description': 'Beginning balance for December', 'reference': 'OB002'},
                {'date': date(2024, 12, 3), 'amount': Decimal('-1200.00'), 'payee': 'Downtown Properties LLC', 'description': 'Monthly office rent payment', 'reference': 'RENT003'},
                {'date': date(2024, 12, 5), 'amount': Decimal('1800.00'), 'payee': 'Holiday Sales Corp', 'description': 'Holiday season consulting work', 'reference': 'HOLIDAY001'},
                {'date': date(2024, 12, 10), 'amount': Decimal('-2900.00'), 'payee': 'Payroll Services Inc', 'description': 'December payroll processing', 'reference': 'PAY003'},
                {'date': date(2024, 12, 15), 'amount': Decimal('2200.00'), 'payee': 'Year-End Clients Inc', 'description': 'Year-end accounting services', 'reference': 'YEAREND001'},
                {'date': date(2024, 12, 20), 'amount': Decimal('-500.00'), 'payee': 'Holiday Bonus Fund', 'description': 'Employee holiday bonuses', 'reference': 'BONUS001'},
                {'date': date(2024, 12, 22), 'amount': Decimal('-150.00'), 'payee': 'Office Holiday Party', 'description': 'Company holiday party expenses', 'reference': 'PARTY001'},
                {'date': date(2024, 12, 28), 'amount': Decimal('800.00'), 'payee': 'Last Minute Client', 'description': 'Rush project completion', 'reference': 'RUSH001'},
            ]
        else:
            transactions_data = []
        
        for i, trans_data in enumerate(transactions_data, 1):
            BankTransaction.objects.create(
                uploaded_file=uploaded_file,
                row_number=i,
                **trans_data
            )
        
        self.stdout.write(f'Created {len(transactions_data)} transactions for {uploaded_file.file_name}')
