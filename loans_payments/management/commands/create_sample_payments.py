from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from company.models import Company
from loans_core.models import Loan
from loans_customers.models import Customer
from loans_payments.models import Payment
import random


class Command(BaseCommand):
    help = 'Create sample payments for testing edit/delete functionality'

    def handle(self, *args, **options):
        try:
            # Get or create company
            company = Company.objects.first()
            if not company:
                self.stdout.write(self.style.ERROR('No company found. Please create a company first.'))
                return

            # Get existing loans or create sample customers and loans
            loans = list(Loan.objects.filter(company=company)[:3])
            
            if not loans:
                # Create sample customers and loans
                for i in range(3):
                    customer, _ = Customer.objects.get_or_create(
                        company=company,
                        customer_id=f'CUST-{i+1:03d}',
                        defaults={
                            'first_name': ['John', 'Jane', 'Mike'][i],
                            'last_name': ['Smith', 'Johnson', 'Wilson'][i],
                            'email': f'customer{i+1}@example.com',
                            'phone': f'555-000-{i+1:03d}',
                            'date_of_birth': date(1990, 1, 1),
                            'created_by_id': 1
                        }
                    )
                    
                    loan, _ = Loan.objects.get_or_create(
                        company=company,
                        loan_number=f'LN-2024-{i+1:03d}',
                        customer=customer,
                        defaults={
                            'loan_amount': Decimal('10000.00'),
                            'current_balance': Decimal('8500.00'),
                            'interest_rate': Decimal('5.50'),
                            'term_months': 36,
                            'status': 'active',
                            'loan_date': date.today() - timedelta(days=180),
                            'created_by_id': 1
                        }
                    )
                    loans.append(loan)

            # Create sample payments
            payment_methods = ['cash', 'check', 'bank_transfer', 'ach', 'credit_card']
            payment_types = ['regular', 'prepayment', 'late_payment']
            
            for i in range(5):
                loan = random.choice(loans)
                amount = Decimal(f'{random.randint(100, 500)}.{random.randint(10, 99)}')
                payment_date = date.today() - timedelta(days=random.randint(1, 30))
                
                payment = Payment.objects.create(
                    company=company,
                    loan=loan,
                    customer=loan.customer,
                    payment_amount=amount,
                    payment_date=payment_date,
                    payment_method=random.choice(payment_methods),
                    payment_type=random.choice(payment_types),
                    reference_number=f'REF-{i+1:04d}',
                    notes=f'Sample payment {i+1} for testing',
                    status='completed',
                    created_by_id=1
                )
                
                self.stdout.write(f'Created payment {payment.payment_id} for ${amount}')

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created 5 sample payments for company: {company.name}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating sample payments: {str(e)}')
            )
