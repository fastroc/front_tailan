"""
Create test payment data for demonstrating the payment processing system
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import date, timedelta

from company.models import Company
from loans_core.models import Loan
from loans_customers.models import Customer
from loans_schedule.models import PaymentSchedule, ScheduledPayment
from loans_payments.models import PaymentPolicy


class Command(BaseCommand):
    help = 'Create test payment data for demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test payment data...'))
        
        # Get or create company
        company, created = Company.objects.get_or_create(
            name='Demo Lending Company',
            defaults={
                'legal_name': 'Demo Lending Company LLC',
                'address_street': '123 Main St',
                'address_city': 'Demo City',
                'address_state': 'DC',
                'address_zip': '12345',
                'phone': '555-0123',
                'email': 'demo@demolending.com',
            }
        )
        
        if created:
            self.stdout.write(f'Created company: {company.name}')
        
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
        
        if created:
            self.stdout.write(f'Created payment policy: {policy.policy_name}')
        
        # Create test customers and loans with different scenarios
        test_customers = [
            {
                'first_name': 'Alice', 'last_name': 'Brown',
                'loan_amount': Decimal('50000.00'), 'current_balance': Decimal('42500.00'),
                'monthly_payment': Decimal('2500.00'), 'interest_rate': Decimal('8.50'),
                'status': 'active',  # Current on payments
                'scenario': 'current'
            },
            {
                'first_name': 'Bob', 'last_name': 'Green',
                'loan_amount': Decimal('35000.00'), 'current_balance': Decimal('28750.00'),
                'monthly_payment': Decimal('1850.00'), 'interest_rate': Decimal('7.25'),
                'status': 'active',  # Will have upcoming payment
                'scenario': 'current'
            },
            {
                'first_name': 'Carol', 'last_name': 'White',
                'loan_amount': Decimal('75000.00'), 'current_balance': Decimal('68200.00'),
                'monthly_payment': Decimal('3200.00'), 'interest_rate': Decimal('9.00'),
                'status': 'active',  # Will test overpayment scenario
                'scenario': 'current'
            },
            {
                'first_name': 'David', 'last_name': 'Black',
                'loan_amount': Decimal('25000.00'), 'current_balance': Decimal('19500.00'),
                'monthly_payment': Decimal('1950.00'), 'interest_rate': Decimal('8.75'),
                'status': 'active',  # Overdue payment with late fees
                'scenario': 'overdue'
            },
            {
                'first_name': 'Emma', 'last_name': 'Wilson',
                'loan_amount': Decimal('60000.00'), 'current_balance': Decimal('52800.00'),
                'monthly_payment': Decimal('2800.00'), 'interest_rate': Decimal('7.50'),
                'status': 'active',  # Partial payment scenario
                'scenario': 'partial'
            },
            {
                'first_name': 'Frank', 'last_name': 'Miller',
                'loan_amount': Decimal('40000.00'), 'current_balance': Decimal('38200.00'),
                'monthly_payment': Decimal('2200.00'), 'interest_rate': Decimal('8.25'),
                'status': 'active',  # Early payment scenario
                'scenario': 'early'
            },
        ]
        
        for i, customer_data in enumerate(test_customers):
            # Create customer
            customer, created = Customer.objects.get_or_create(
                company=company,
                first_name=customer_data['first_name'],
                last_name=customer_data['last_name'],
                defaults={
                    'email': f"{customer_data['first_name'].lower()}.{customer_data['last_name'].lower()}@email.com",
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
            
            if created:
                self.stdout.write(f'Created customer: {customer.full_name}')
            
            # Create loan
            loan_number = f'LN-{2025}{100 + i:03d}'
            loan, created = Loan.objects.get_or_create(
                company=company,
                loan_number=loan_number,
                defaults={
                    'customer': customer,
                    'loan_amount': customer_data['loan_amount'],
                    'current_balance': customer_data['current_balance'],
                    'interest_rate': customer_data['interest_rate'],
                    'loan_term_months': 24,
                    'status': customer_data['status'],
                    'origination_date': date.today() - timedelta(days=180 + i*30),
                    'first_payment_date': date.today() - timedelta(days=150 + i*30),
                    'maturity_date': date.today() + timedelta(days=365 + i*30),
                }
            )
            
            if created:
                self.stdout.write(f'Created loan: {loan.loan_number}')
                
                # Create payment schedule
                schedule, schedule_created = PaymentSchedule.objects.get_or_create(
                    company=company,
                    loan=loan,
                    defaults={
                        'schedule_type': 'equal_payment',
                        'payment_frequency': 'monthly',
                        'total_payments': 24,
                        'payments_completed': 6 + i,
                        'total_principal': customer_data['loan_amount'],
                        'total_interest': customer_data['loan_amount'] * Decimal('0.15'),
                        'total_amount': customer_data['loan_amount'] * Decimal('1.15'),
                    }
                )
                
                if schedule_created:
                    # Create upcoming scheduled payments with different scenarios
                    today = date.today()
                    for j in range(3):  # Create next 3 payments
                        # Different scenarios for different customers
                        if customer_data['scenario'] == 'overdue':
                            # David Black - overdue payment
                            due_date = today - timedelta(days=15) if j == 0 else today + timedelta(days=30*j - 15)
                            payment_status = 'overdue' if j == 0 else 'scheduled'
                        elif customer_data['scenario'] == 'partial':
                            # Emma Wilson - partial payment made
                            due_date = today + timedelta(days=30*j)
                            payment_status = 'partial' if j == 0 else 'scheduled'
                        elif customer_data['scenario'] == 'early':
                            # Frank Miller - early payment due
                            due_date = today + timedelta(days=30*j - 5)
                            payment_status = 'scheduled'
                        else:
                            # Current payments
                            due_date = today + timedelta(days=30*j)
                            payment_status = 'scheduled'
                        
                        # Calculate payment breakdown (simplified)
                        interest_amount = customer_data['current_balance'] * customer_data['interest_rate'] / Decimal('100') / Decimal('12')
                        principal_amount = customer_data['monthly_payment'] - interest_amount
                        
                        scheduled_payment = ScheduledPayment.objects.create(
                            company=company,
                            payment_schedule=schedule,
                            loan=loan,
                            payment_number=7 + i + j,
                            due_date=due_date,
                            principal_amount=principal_amount,
                            interest_amount=interest_amount,
                            total_amount=customer_data['monthly_payment'],
                            beginning_balance=customer_data['current_balance'],
                            ending_balance=customer_data['current_balance'] - principal_amount,
                            status=payment_status
                        )
                        
                        # Add scenario-specific details
                        if customer_data['scenario'] == 'overdue' and j == 0:
                            # David's overdue payment with late fees
                            scheduled_payment.days_overdue = 15
                            scheduled_payment.late_fees_assessed = Decimal('25.00')
                            scheduled_payment.save()
                        elif customer_data['scenario'] == 'partial' and j == 0:
                            # Emma's partial payment
                            scheduled_payment.amount_paid = customer_data['monthly_payment'] * Decimal('0.6')  # 60% paid
                            scheduled_payment.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test data:\n'
                f'- 1 company: {company.name}\n'
                f'- 1 payment policy: {policy.policy_name}\n'
                f'- {len(test_customers)} customers and loans with different scenarios:\n'
                f'  * Alice Brown (LN-2025100): Current on payments\n'
                f'  * Bob Green (LN-2025101): Current on payments\n'
                f'  * Carol White (LN-2025102): Current (good for overpayment testing)\n'
                f'  * David Black (LN-2025103): OVERDUE payment with late fees\n'
                f'  * Emma Wilson (LN-2025104): PARTIAL payment made\n'
                f'  * Frank Miller (LN-2025105): Early payment due\n'
                f'- Payment schedules with various scenarios\n'
                f'- Ready for testing different payment types!'
            )
        )
