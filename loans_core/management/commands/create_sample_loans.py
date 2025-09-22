from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from company.models import Company
from loans_core.models import LoanProduct, LoanApplication, Loan
from loans_customers.models import Customer


class Command(BaseCommand):
    help = 'Create sample loan data for testing'

    def handle(self, *args, **options):
        # Get or create a company
        company, created = Company.objects.get_or_create(
            name='Demo Loan Company',
            defaults={
                'address': '123 Main St',
                'city': 'Demo City',
                'state': 'Demo State',
                'zip_code': '12345',
                'phone': '555-0123',
                'email': 'demo@example.com'
            }
        )
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()

        # Create loan products if they don't exist
        loan_products = []
        products_data = [
            {'name': 'Personal Loan', 'code': 'PL001', 'category': 'personal', 'min_amount': 1000, 'max_amount': 50000, 'rate': 12.5},
            {'name': 'Business Loan', 'code': 'BL001', 'category': 'business', 'min_amount': 5000, 'max_amount': 200000, 'rate': 10.0},
            {'name': 'Auto Loan', 'code': 'AL001', 'category': 'auto', 'min_amount': 10000, 'max_amount': 100000, 'rate': 8.5},
        ]
        
        for product_data in products_data:
            product, created = LoanProduct.objects.get_or_create(
                company=company,
                code=product_data['code'],
                defaults={
                    'name': product_data['name'],
                    'category': product_data['category'],
                    'min_amount': Decimal(str(product_data['min_amount'])),
                    'max_amount': Decimal(str(product_data['max_amount'])),
                    'min_term_months': 6,
                    'max_term_months': 60,
                    'default_interest_rate': Decimal(str(product_data['rate'])),
                    'requires_collateral': False,
                    'is_active': True,
                    'created_by': admin_user
                }
            )
            loan_products.append(product)

        # Create sample customers
        customers_data = [
            {'first_name': 'John', 'last_name': 'Smith', 'email': 'john.smith@email.com', 'national_id': 'ID001'},
            {'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah.johnson@email.com', 'national_id': 'ID002'},
            {'first_name': 'Michael', 'last_name': 'Brown', 'email': 'michael.brown@email.com', 'national_id': 'ID003'},
            {'first_name': 'Emily', 'last_name': 'Davis', 'email': 'emily.davis@email.com', 'national_id': 'ID004'},
            {'first_name': 'David', 'last_name': 'Wilson', 'email': 'david.wilson@email.com', 'national_id': 'ID005'},
        ]
        
        customers = []
        for i, customer_data in enumerate(customers_data):
            customer, created = Customer.objects.get_or_create(
                company=company,
                national_id=customer_data['national_id'],
                defaults={
                    'first_name': customer_data['first_name'],
                    'last_name': customer_data['last_name'],
                    'email': customer_data['email'],
                    'phone': f'555-010{i+1}',
                    'address': f'{i+1}23 Sample St',
                    'city': 'Demo City',
                    'state': 'Demo State',
                    'zip_code': '12345',
                    'date_of_birth': date(1990, 1, 1) + timedelta(days=i*365),
                    'employment_type': 'full_time',
                    'annual_income': Decimal('50000.00'),
                    'created_by': admin_user
                }
            )
            customers.append(customer)

        # Create sample loans
        loans_data = [
            {'customer_idx': 0, 'product_idx': 0, 'amount': 4250, 'term': 24, 'disbursed': True},
            {'customer_idx': 1, 'product_idx': 1, 'amount': 8900, 'term': 36, 'disbursed': True},
            {'customer_idx': 2, 'product_idx': 2, 'amount': 12750, 'term': 48, 'disbursed': True},
            {'customer_idx': 3, 'product_idx': 0, 'amount': 6300, 'term': 30, 'disbursed': True},
            {'customer_idx': 4, 'product_idx': 1, 'amount': 9850, 'term': 42, 'disbursed': True},
        ]
        
        for i, loan_data in enumerate(loans_data):
            customer = customers[loan_data['customer_idx']]
            product = loan_products[loan_data['product_idx']]
            
            # Create loan application first
            application, created = LoanApplication.objects.get_or_create(
                company=company,
                customer=customer,
                loan_product=product,
                defaults={
                    'requested_amount': Decimal(str(loan_data['amount'])),
                    'requested_term': loan_data['term'],
                    'purpose': f'Sample loan purpose for {customer.first_name}',
                    'monthly_income': Decimal('4000.00'),
                    'status': 'approved',
                    'approved_amount': Decimal(str(loan_data['amount'])),
                    'approved_term': loan_data['term'],
                    'approved_rate': product.default_interest_rate,
                    'approval_date': timezone.now().date(),
                    'created_by': admin_user
                }
            )
            
            if loan_data['disbursed'] and created:
                # Calculate monthly payment (simple calculation)
                principal = application.approved_amount
                rate = application.approved_rate / Decimal('100') / Decimal('12')  # Monthly rate
                term = application.approved_term
                
                # Simple monthly payment calculation
                if rate > 0:
                    monthly_payment = principal * (rate * (1 + rate) ** term) / ((1 + rate) ** term - 1)
                else:
                    monthly_payment = principal / term
                
                # Create the loan
                loan_number = f'DL202500{i+1}'
                disbursement_date = timezone.now().date() - timedelta(days=30*(i+1))
                
                loan, loan_created = Loan.objects.get_or_create(
                    company=company,
                    loan_number=loan_number,
                    defaults={
                        'application': application,
                        'customer': customer,
                        'loan_product': product,
                        'principal_amount': principal,
                        'current_balance': principal * Decimal('0.8'),  # 80% remaining
                        'interest_rate': application.approved_rate,
                        'term_months': term,
                        'monthly_payment': monthly_payment.quantize(Decimal('0.01')),
                        'disbursement_date': disbursement_date,
                        'first_payment_date': disbursement_date + timedelta(days=30),
                        'maturity_date': disbursement_date + timedelta(days=30*term),
                        'next_payment_date': timezone.now().date() + timedelta(days=7),
                        'payments_remaining': term - 3,  # 3 payments made
                        'payments_made': 3,
                        'total_payments_received': monthly_payment * 3,
                        'status': 'active',
                        'created_by': admin_user
                    }
                )
                
                if loan_created:
                    self.stdout.write(f"Created loan {loan.loan_number} for {customer.first_name} {customer.last_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data:\n'
                f'- Company: {company.name}\n'
                f'- Loan Products: {len(loan_products)}\n'
                f'- Customers: {len(customers)}\n'
                f'- Loans: {Loan.objects.filter(company=company).count()}'
            )
        )
