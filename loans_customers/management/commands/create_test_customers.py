from django.core.management.base import BaseCommand
from django.db import transaction
from company.models import Company
from loans_customers.models import Customer
from datetime import date


class Command(BaseCommand):
    help = 'Create test customers for bulk loan application testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating test customers with Cyrillic names...')
        
        # Get first company for testing
        company = Company.objects.first()
        if not company:
            self.stdout.write(self.style.ERROR('No companies found. Please create a company first.'))
            return

        # Test customers with Cyrillic names
        test_customers = [
            {
                'national_id': 'УБ12345001',
                'first_name': 'Батбаяр',
                'last_name': 'Ганбат',
                'phone_primary': '+976-99123456',
                'email': 'batbayar@email.mn',
                'date_of_birth': date(1985, 3, 15),
                'street_address': 'Улаанбаатар хот, 1-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
            {
                'national_id': 'МН87654002',
                'first_name': 'Цэцэгмаа',
                'last_name': 'Доржсүрэн',
                'phone_primary': '+976-99234567',
                'email': 'tsetsegmaa@email.mn',
                'date_of_birth': date(1990, 7, 22),
                'street_address': 'Улаанбаатар хот, 2-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
            {
                'national_id': 'АА98765003',
                'first_name': 'Ганболд',
                'last_name': 'Батмөнх',
                'phone_primary': '+976-99345678',
                'email': 'ganbold@email.mn',
                'date_of_birth': date(1978, 12, 10),
                'street_address': 'Улаанбаатар хот, 3-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
            {
                'national_id': 'БГ11223004',
                'first_name': 'Сайнбаяр',
                'last_name': 'Түмэнбаяр',
                'phone_primary': '+976-99456789',
                'email': 'sainbayar@email.mn',
                'date_of_birth': date(1982, 5, 8),
                'street_address': 'Улаанбаатар хот, 4-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
            {
                'national_id': 'ТҮ55443305',
                'first_name': 'Оюунбилэг',
                'last_name': 'Пүрэвсүрэн',
                'phone_primary': '+976-99567890',
                'email': 'oyunbileg@email.mn',
                'date_of_birth': date(1995, 1, 30),
                'street_address': 'Улаанбаатар хот, 5-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
            {
                'national_id': 'ЭР66778806',
                'first_name': 'Баасандорж',
                'last_name': 'Батбаяр',
                'phone_primary': '+976-99678901',
                'email': 'baasandorj@email.mn',
                'date_of_birth': date(1975, 9, 14),
                'street_address': 'Улаанбаатар хот, 6-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
            {
                'national_id': 'ХМ99887707',
                'first_name': 'Мөнхбаяр',
                'last_name': 'Дорждагва',
                'phone_primary': '+976-99789012',
                'email': 'munkbayar@email.mn',
                'date_of_birth': date(1988, 11, 25),
                'street_address': 'Улаанбаатар хот, 7-р хороо',
                'city': 'Улаанбаатар',
                'state_province': 'Улаанбаатар',
                'postal_code': '14200',
            },
        ]

        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            self.stdout.write(f'Processing customers for company: {company.name}')
            
            for customer_data in test_customers:
                national_id = customer_data['national_id']
                
                # Check if customer already exists
                customer, created = Customer.objects.get_or_create(
                    company=company,
                    national_id=national_id,
                    defaults=customer_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ Created {customer.first_name} {customer.last_name} ({national_id})')
                    )
                else:
                    # Update existing customer
                    update_data = {k: v for k, v in customer_data.items() if k not in ['national_id']}
                    for field, value in update_data.items():
                        setattr(customer, field, value)
                    customer.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'  🔄 Updated {customer.first_name} {customer.last_name} ({national_id})')
                    )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} customers'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count} customers'))
        self.stdout.write(self.style.SUCCESS(f'  Company: {company.name}'))
        
        # Display created customers
        self.stdout.write('\n👥 CREATED TEST CUSTOMERS:')
        customers = Customer.objects.filter(company=company).order_by('first_name')
        for customer in customers:
            self.stdout.write(
                f'  {customer.national_id} - {customer.first_name} {customer.last_name} '
                f'({customer.phone_primary}, {customer.email})'
            )
