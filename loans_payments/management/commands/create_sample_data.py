from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from company.models import Company, UserCompanyProfile
from loans_customers.models import Customer
from loans_core.models import Loan, LoanProduct
from loans_schedule.models import ScheduledPayment
from loans_payments.models import Payment


class Command(BaseCommand):
    help = 'Create sample data for payment demo - users, loans, schedules, and payments'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample payment demo data...'))
        
        # Get or create company
        company, created = Company.objects.get_or_create(
            name='Demo Loan Company',
            defaults={
                'email': 'demo@loansystem.com',
                'phone': '+1-555-0123',
                'address': '123 Finance Street, Demo City, DC 12345'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created company: {company.name}')
        else:
            self.stdout.write(f'✅ Using existing company: {company.name}')

        # Create demo users
        demo_users = []
        for i in range(3):
            username = f'demo_user_{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': f'Demo',
                    'last_name': f'User {i+1}',
                    'email': f'demo{i+1}@loansystem.com',
                    'is_staff': True,
                    'is_active': True
                }
            )
            if created:
                user.set_password('demo123')
                user.save()
                self.stdout.write(f'✅ Created user: {username} (password: demo123)')
            
            # Link to company
            profile, created = UserCompanyProfile.objects.get_or_create(
                user=user,
                defaults={'company': company}
            )
            demo_users.append(user)

        # Create loan product
        loan_product, created = LoanProduct.objects.get_or_create(
            company=company,
            name='Demo Personal Loan',
            defaults={
                'code': 'DPL001',
                'description': 'Demo personal loan for testing',
                'min_amount': Decimal('1000.00'),
                'max_amount': Decimal('50000.00'),
                'interest_rate': Decimal('12.50'),
                'term_months': 24,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created loan product: {loan_product.name}')

        # Create demo customers
        customers_data = [
            {'first_name': 'John', 'last_name': 'Smith', 'email': 'john.smith@email.com', 'phone': '+1-555-0101'},
            {'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah.johnson@email.com', 'phone': '+1-555-0102'},
            {'first_name': 'Michael', 'last_name': 'Brown', 'email': 'michael.brown@email.com', 'phone': '+1-555-0103'},
            {'first_name': 'Emily', 'last_name': 'Davis', 'email': 'emily.davis@email.com', 'phone': '+1-555-0104'},
            {'first_name': 'David', 'last_name': 'Wilson', 'email': 'david.wilson@email.com', 'phone': '+1-555-0105'},
        ]
        
        customers = []
        for customer_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                company=company,
                email=customer_data['email'],
                defaults=customer_data
            )
            if created:
                self.stdout.write(f'✅ Created customer: {customer.first_name} {customer.last_name}')
            customers.append(customer)

        # Create demo loans
        today = timezone.now().date()
        loans = []
        
        loan_amounts = [Decimal('5000.00'), Decimal('10000.00'), Decimal('15000.00'), Decimal('7500.00'), Decimal('12000.00')]
        
        for i, customer in enumerate(customers):
            loan_number = f'DL{2025}{1000 + i}'
            loan, created = Loan.objects.get_or_create(
                company=company,
                loan_number=loan_number,
                defaults={
                    'customer': customer,
                    'loan_product': loan_product,
                    'principal_amount': loan_amounts[i],
                    'interest_rate': Decimal('12.50'),
                    'term_months': 24,
                    'application_date': today - timedelta(days=random.randint(30, 90)),
                    'approval_date': today - timedelta(days=random.randint(20, 60)),
                    'disbursement_date': today - timedelta(days=random.randint(10, 45)),
                    'status': 'active',
                    'created_by': demo_users[0]
                }
            )
            if created:
                self.stdout.write(f'✅ Created loan: {loan_number} for {customer.first_name} {customer.last_name}')
            loans.append(loan)

        # Create scheduled payments
        self.stdout.write('Creating scheduled payments...')
        for loan in loans:
            monthly_payment = loan.principal_amount / 24 * Decimal('1.1')  # Simple calculation with interest
            
            for month in range(1, 25):  # 24 months
                due_date = loan.disbursement_date + timedelta(days=30 * month)
                
                # Determine status based on due date
                if due_date < today - timedelta(days=30):
                    status = 'paid'
                elif due_date < today:
                    status = random.choice(['overdue', 'partial', 'paid'])
                elif due_date <= today + timedelta(days=7):
                    status = 'scheduled'
                else:
                    status = 'scheduled'
                
                scheduled_payment, created = ScheduledPayment.objects.get_or_create(
                    loan=loan,
                    due_date=due_date,
                    defaults={
                        'principal_amount': loan.principal_amount / 24,
                        'interest_amount': loan.principal_amount / 24 * Decimal('0.1'),
                        'total_amount': monthly_payment,
                        'status': status,
                        'payment_number': month
                    }
                )

        # Create sample payments
        self.stdout.write('Creating sample payments...')
        payment_methods = ['cash', 'check', 'bank_transfer', 'online']
        
        # Payments for today (to show in "Payments Today")
        for i in range(3):
            loan = random.choice(loans)
            amount = Decimal(str(random.randint(200, 800))) + Decimal('0.00')
            
            payment, created = Payment.objects.get_or_create(
                company=company,
                loan=loan,
                customer=loan.customer,
                payment_date=today,
                defaults={
                    'payment_amount': amount,
                    'payment_method': random.choice(payment_methods),
                    'reference_number': f'PAY{today.strftime("%Y%m%d")}{1000 + i}',
                    'notes': f'Sample payment #{i+1} for today',
                    'status': 'completed',
                    'processed_by': demo_users[0],
                    'created_by': demo_users[0]
                }
            )
            if created:
                self.stdout.write(f'✅ Created today\'s payment: ${amount} for loan {loan.loan_number}')

        # Payments for this month (to show in "Monthly Collection")
        for i in range(8):
            loan = random.choice(loans)
            amount = Decimal(str(random.randint(300, 1200))) + Decimal('0.00')
            payment_date = today - timedelta(days=random.randint(1, 28))
            
            # Skip if payment already exists for this date and loan
            if not Payment.objects.filter(loan=loan, payment_date=payment_date).exists():
                payment = Payment.objects.create(
                    company=company,
                    loan=loan,
                    customer=loan.customer,
                    payment_amount=amount,
                    payment_date=payment_date,
                    payment_method=random.choice(payment_methods),
                    reference_number=f'PAY{payment_date.strftime("%Y%m%d")}{2000 + i}',
                    notes=f'Sample monthly payment #{i+1}',
                    status='completed',
                    processed_by=demo_users[0],
                    created_by=demo_users[0]
                )
                self.stdout.write(f'✅ Created monthly payment: ${amount} on {payment_date} for loan {loan.loan_number}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n🎉 Sample data creation completed!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Created:'))
        self.stdout.write(f'   • Company: {company.name}')
        self.stdout.write(f'   • Users: {len(demo_users)} demo users')
        self.stdout.write(f'   • Customers: {len(customers)} customers')
        self.stdout.write(f'   • Loans: {len(loans)} active loans')
        self.stdout.write(f'   • Payments: Multiple payments for today and this month')
        
        self.stdout.write(self.style.SUCCESS('\n🔑 Login credentials:'))
        for user in demo_users:
            self.stdout.write(f'   • Username: {user.username} | Password: demo123')
        
        self.stdout.write(self.style.SUCCESS(f'\n🌐 Visit: http://localhost:8000/loans/payments/'))
        self.stdout.write(self.style.SUCCESS('📈 Your statistics should now show real data!'))
