"""
Create test loan applications and approve them for payment testing
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import date, timedelta

from company.models import Company
from loans_core.models import Loan, LoanProduct
from loans_customers.models import Customer
from loans_schedule.models import PaymentSchedule, ScheduledPayment
from loans_payments.models import PaymentPolicy


class Command(BaseCommand):
    help = 'Create approved/disbursed loans for payment testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating approved loans for payment testing...'))
        
        # Get or create company
        company = Company.objects.first()
        if not company:
            company = Company.objects.create(
                name='Demo Lending Company',
                legal_name='Demo Lending Company LLC',
                address_street='123 Main St',
                address_city='Demo City',
                address_state='DC',
                address_zip='12345',
                phone='555-0123',
                email='demo@demolending.com',
            )
            self.stdout.write(f'Created company: {company.name}')
        
        # Get or create loan product
        loan_product, created = LoanProduct.objects.get_or_create(
            company=company,
            product_name='Personal Loan',
            defaults={
                'product_code': 'PL001',
                'description': 'Standard personal loan product',
                'min_loan_amount': Decimal('1000.00'),
                'max_loan_amount': Decimal('100000.00'),
                'default_interest_rate': Decimal('8.50'),
                'min_term_months': 6,
                'max_term_months': 60,
                'is_active': True,
            }
        )
        
        # Create payment policy
        policy, created = PaymentPolicy.objects.get_or_create(
            company=company,
            policy_name='Standard Payment Policy',
            defaults={
                'description': 'Standard industry payment processing rules',
                'is_default': True,
                'allocation_method': 'interest_first',
                'grace_period_days': 10,
                'late_fee_amount': Decimal('25.00'),
                'prepayment_to_principal': True,
            }
        )
        
        # Create test borrowers with different scenarios
        test_borrowers = [
            {
                'first_name': 'Alice', 'last_name': 'Brown',
                'loan_amount': Decimal('50000.00'), 'current_balance': Decimal('42500.00'),
                'monthly_payment': Decimal('2500.00'), 'interest_rate': Decimal('8.50'),
                'scenario': 'current', 'term': 24
            },
            {
                'first_name': 'Bob', 'last_name': 'Green',
                'loan_amount': Decimal('35000.00'), 'current_balance': Decimal('28750.00'),
                'monthly_payment': Decimal('1850.00'), 'interest_rate': Decimal('7.25'),
                'scenario': 'current', 'term': 24
            },
            {
                'first_name': 'Carol', 'last_name': 'White',
                'loan_amount': Decimal('75000.00'), 'current_balance': Decimal('68200.00'),
                'monthly_payment': Decimal('3200.00'), 'interest_rate': Decimal('9.00'),
                'scenario': 'current', 'term': 30
            },
            {
                'first_name': 'David', 'last_name': 'Black',
                'loan_amount': Decimal('25000.00'), 'current_balance': Decimal('19500.00'),
                'monthly_payment': Decimal('1950.00'), 'interest_rate': Decimal('8.75'),
                'scenario': 'overdue', 'term': 18
            },
            {
                'first_name': 'Emma', 'last_name': 'Wilson',
                'loan_amount': Decimal('60000.00'), 'current_balance': Decimal('52800.00'),
                'monthly_payment': Decimal('2800.00'), 'interest_rate': Decimal('7.50'),
                'scenario': 'partial', 'term': 36
            },
            {
                'first_name': 'Frank', 'last_name': 'Miller',
                'loan_amount': Decimal('40000.00'), 'current_balance': Decimal('38200.00'),
                'monthly_payment': Decimal('2200.00'), 'interest_rate': Decimal('8.25'),
                'scenario': 'early', 'term': 24
            },
        ]
        
        loans_created = 0
        for i, borrower_data in enumerate(test_borrowers):
            # Create or get customer
            customer, created = Customer.objects.get_or_create(
                company=company,
                first_name=borrower_data['first_name'],
                last_name=borrower_data['last_name'],
                defaults={
                    'email': f"{borrower_data['first_name'].lower()}.{borrower_data['last_name'].lower()}@email.com",
                    'phone': f'555-{1000 + i:04d}',
                    'address_street': f'{100 + i*10} Demo Street',
                    'address_city': 'Demo City',
                    'address_state': 'DC',
                    'address_zip': '12345',
                    'date_of_birth': date(1980 + i, 1 + i, 15),
                    'employment_status': 'employed',
                    'annual_income': Decimal('60000.00'),
                }
            )
            
            # Create loan in disbursed status
            loan_number = f'LN-{2025}{100 + i:03d}'
            loan, created = Loan.objects.get_or_create(
                company=company,
                loan_number=loan_number,
                defaults={
                    'customer': customer,
                    'loan_product': loan_product,
                    'loan_amount': borrower_data['loan_amount'],
                    'current_balance': borrower_data['current_balance'],
                    'interest_rate': borrower_data['interest_rate'],
                    'loan_term_months': borrower_data['term'],
                    'status': 'active',  # Active loans are disbursed and can receive payments
                    'origination_date': date.today() - timedelta(days=180 + i*30),
                    'first_payment_date': date.today() - timedelta(days=150 + i*30),
                    'maturity_date': date.today() + timedelta(days=365 + i*30),
                }
            )
            
            if created:
                loans_created += 1
                self.stdout.write(f'Created loan: {loan.loan_number} for {customer.full_name}')
                
                # Create payment schedule
                schedule = PaymentSchedule.objects.create(
                    company=company,
                    loan=loan,
                    schedule_type='equal_payment',
                    payment_frequency='monthly',
                    total_payments=borrower_data['term'],
                    payments_completed=6 + i,
                    total_principal=borrower_data['loan_amount'],
                    total_interest=borrower_data['loan_amount'] * Decimal('0.15'),
                    total_amount=borrower_data['loan_amount'] * Decimal('1.15'),
                )
                
                # Create upcoming scheduled payments
                today = date.today()
                for j in range(3):  # Create next 3 payments
                    # Different scenarios for different customers
                    if borrower_data['scenario'] == 'overdue':
                        due_date = today - timedelta(days=15) if j == 0 else today + timedelta(days=30*j - 15)
                        payment_status = 'overdue' if j == 0 else 'scheduled'
                    elif borrower_data['scenario'] == 'partial':
                        due_date = today + timedelta(days=30*j)
                        payment_status = 'partial' if j == 0 else 'scheduled'
                    elif borrower_data['scenario'] == 'early':
                        due_date = today + timedelta(days=30*j - 5)
                        payment_status = 'scheduled'
                    else:
                        due_date = today + timedelta(days=30*j)
                        payment_status = 'scheduled'
                    
                    # Calculate payment breakdown
                    interest_amount = borrower_data['current_balance'] * borrower_data['interest_rate'] / Decimal('100') / Decimal('12')
                    principal_amount = borrower_data['monthly_payment'] - interest_amount
                    
                    scheduled_payment = ScheduledPayment.objects.create(
                        company=company,
                        payment_schedule=schedule,
                        loan=loan,
                        payment_number=7 + i + j,
                        due_date=due_date,
                        principal_amount=principal_amount,
                        interest_amount=interest_amount,
                        total_amount=borrower_data['monthly_payment'],
                        beginning_balance=borrower_data['current_balance'],
                        ending_balance=borrower_data['current_balance'] - principal_amount,
                        status=payment_status
                    )
                    
                    # Add scenario-specific details
                    if borrower_data['scenario'] == 'overdue' and j == 0:
                        scheduled_payment.days_overdue = 15
                        scheduled_payment.late_fees_assessed = Decimal('25.00')
                        scheduled_payment.save()
                    elif borrower_data['scenario'] == 'partial' and j == 0:
                        scheduled_payment.amount_paid = borrower_data['monthly_payment'] * Decimal('0.6')
                        scheduled_payment.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {loans_created} approved/disbursed loans:\n'
                f'- Alice Brown (LN-2025100): Current payments - $2,500/month\n'
                f'- Bob Green (LN-2025101): Current payments - $1,850/month\n'
                f'- Carol White (LN-2025102): Current payments - $3,200/month\n'
                f'- David Black (LN-2025103): OVERDUE payment + late fees\n'
                f'- Emma Wilson (LN-2025104): PARTIAL payment made\n'
                f'- Frank Miller (LN-2025105): Early payment due\n\n'
                f'These loans are now available in the payment system!\n'
                f'Visit: http://localhost:8000/loans/payments/'
            )
        )
