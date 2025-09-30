from django.core.management.base import BaseCommand
from django.db import transaction
from company.models import Company
from loans_core.models import LoanProduct
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create default loan products for all companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Create products for specific company ID only',
        )

    def handle(self, *args, **options):
        self.stdout.write('Creating default loan products...')
        
        # Get companies to create products for
        if options['company_id']:
            companies = Company.objects.filter(id=options['company_id'])
            if not companies.exists():
                self.stdout.write(
                    self.style.ERROR(f'Company with ID {options["company_id"]} not found')
                )
                return
        else:
            companies = Company.objects.all()
        
        if not companies.exists():
            self.stdout.write(self.style.ERROR('No companies found. Please create a company first.'))
            return

        # Default loan products to create
        loan_products = [
            {
                'code': 'PL001',
                'name': 'Personal Loan - Standard',
                'category': 'personal',
                'description': 'Standard personal loan for general purposes',
                'min_amount': Decimal('10000.00'),
                'max_amount': Decimal('500000.00'),
                'min_term_months': 6,
                'max_term_months': 60,
                'default_interest_rate': Decimal('12.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('0.00'),
                'grace_period_days': 10,
                'late_fee_amount': Decimal('25.00'),
                'late_fee_percentage': Decimal('5.00'),
                'is_active': True,
            },
            {
                'code': 'BL001',
                'name': 'Business Loan - SME',
                'category': 'business',
                'description': 'Small and medium enterprise business loan',
                'min_amount': Decimal('50000.00'),
                'max_amount': Decimal('2000000.00'),
                'min_term_months': 12,
                'max_term_months': 120,
                'default_interest_rate': Decimal('15.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('1.00'),
                'grace_period_days': 15,
                'late_fee_amount': Decimal('50.00'),
                'late_fee_percentage': Decimal('5.00'),
                'is_active': True,
            },
            {
                'code': 'AL001',
                'name': 'Auto Loan - Vehicle Purchase',
                'category': 'auto',
                'description': 'Vehicle purchase financing',
                'min_amount': Decimal('20000.00'),
                'max_amount': Decimal('1000000.00'),
                'min_term_months': 12,
                'max_term_months': 84,
                'default_interest_rate': Decimal('10.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('0.50'),
                'grace_period_days': 10,
                'late_fee_amount': Decimal('30.00'),
                'late_fee_percentage': Decimal('3.00'),
                'is_active': True,
            },
            {
                'code': 'ML001',
                'name': 'Mortgage Loan - Home Purchase',
                'category': 'mortgage',
                'description': 'Home purchase and refinancing mortgage',
                'min_amount': Decimal('100000.00'),
                'max_amount': Decimal('10000000.00'),
                'min_term_months': 60,
                'max_term_months': 360,
                'default_interest_rate': Decimal('8.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('2.00'),
                'grace_period_days': 15,
                'late_fee_amount': Decimal('100.00'),
                'late_fee_percentage': Decimal('5.00'),
                'is_active': True,
            },
            {
                'code': 'SL001',
                'name': 'Student Loan - Education',
                'category': 'education',
                'description': 'Educational expenses and tuition financing',
                'min_amount': Decimal('5000.00'),
                'max_amount': Decimal('200000.00'),
                'min_term_months': 6,
                'max_term_months': 120,
                'default_interest_rate': Decimal('6.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('0.00'),
                'grace_period_days': 30,
                'late_fee_amount': Decimal('15.00'),
                'late_fee_percentage': Decimal('3.00'),
                'is_active': True,
            },
            {
                'code': 'EL001',
                'name': 'Emergency Loan - Quick Cash',
                'category': 'personal',
                'description': 'Fast processing emergency loan',
                'min_amount': Decimal('5000.00'),
                'max_amount': Decimal('100000.00'),
                'min_term_months': 1,
                'max_term_months': 24,
                'default_interest_rate': Decimal('18.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('0.00'),
                'grace_period_days': 5,
                'late_fee_amount': Decimal('50.00'),
                'late_fee_percentage': Decimal('10.00'),
                'is_active': True,
            },
            {
                'code': 'CL001',
                'name': 'Custom Loan - Flexible Terms',
                'category': 'personal',
                'description': 'Highly flexible loan product with customizable rates and terms',
                'min_amount': Decimal('1000.00'),
                'max_amount': Decimal('50000000.00'),
                'min_term_months': 1,
                'max_term_months': 180,
                'default_interest_rate': Decimal('25.00'),
                'allows_prepayment': True,
                'prepayment_penalty_rate': Decimal('0.00'),
                'grace_period_days': 15,
                'late_fee_amount': Decimal('100.00'),
                'late_fee_percentage': Decimal('5.00'),
                'is_active': True,
            },
        ]

        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for company in companies:
                self.stdout.write(f'\nProcessing company: {company.name}')
                
                for product_data in loan_products:
                    code = product_data['code']
                    
                    # Check if product already exists for this company
                    loan_product, created = LoanProduct.objects.get_or_create(
                        company=company,
                        code=code,
                        defaults=product_data
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ Created {code}: {product_data["name"]}')
                        )
                    else:
                        # Update existing product with new data (except company and code)
                        update_data = {k: v for k, v in product_data.items() if k not in ['code']}
                        for field, value in update_data.items():
                            setattr(loan_product, field, value)
                        loan_product.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'  🔄 Updated {code}: {product_data["name"]}')
                        )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} loan products'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count} loan products'))
        self.stdout.write(self.style.SUCCESS(f'  Companies processed: {companies.count()}'))
        
        # Display available products
        self.stdout.write('\n📋 AVAILABLE LOAN PRODUCTS:')
        for company in companies:
            self.stdout.write(f'\n🏢 {company.name}:')
            products = LoanProduct.objects.filter(company=company, is_active=True).order_by('code')
            for product in products:
                self.stdout.write(
                    f'  {product.code} - {product.name} '
                    f'({product.default_interest_rate}% APR, '
                    f'{product.min_term_months}-{product.max_term_months} months)'
                )
