"""
Custom management command to migrate data from SQLite to PostgreSQL
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from loans_customers.models import Customer
from company.models import Company


class Command(BaseCommand):
    help = 'Migrate data from SQLite to PostgreSQL'

    def handle(self, *args, **options):
        # Temporarily switch to SQLite to read data
        sqlite_db = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': settings.BASE_DIR / 'db.sqlite3',
        }
        
        # Store original database config
        original_db = settings.DATABASES['default'].copy()
        
        try:
            # Switch to SQLite
            settings.DATABASES['default'] = sqlite_db
            
            # Import Django's connection handling
            from django.db import connections
            
            # Close existing connections
            connections.close_all()
            
            self.stdout.write("Reading data from SQLite...")
            
            # Read all users
            users_data = list(User.objects.all().values())
            companies_data = list(Company.objects.all().values()) if Company.objects.exists() else []
            customers_data = list(Customer.objects.all().values()) if Customer.objects.exists() else []
            
            self.stdout.write(f"Found {len(users_data)} users, {len(companies_data)} companies, {len(customers_data)} customers")
            
        finally:
            # Switch back to PostgreSQL
            settings.DATABASES['default'] = original_db
            connections.close_all()
        
        # Now write to PostgreSQL
        self.stdout.write("Writing data to PostgreSQL...")
        
        with transaction.atomic():
            # Create users first
            for user_data in users_data:
                user_data.pop('id')  # Remove old ID
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults=user_data
                )
                if created:
                    self.stdout.write(f"Created user: {user.username}")
            
            # Create companies
            for company_data in companies_data:
                company_data.pop('id')  # Remove old ID
                company, created = Company.objects.get_or_create(
                    name=company_data['name'],
                    defaults=company_data
                )
                if created:
                    self.stdout.write(f"Created company: {company.name}")
            
            # Create customers
            for customer_data in customers_data:
                customer_data.pop('id')  # Remove old ID
                # Get the company if it exists
                company_id = customer_data.get('company_id')
                if company_id:
                    try:
                        customer_data['company'] = Company.objects.get(id=company_id)
                        customer_data.pop('company_id')
                    except Company.DoesNotExist:
                        customer_data.pop('company_id', None)
                
                customer, created = Customer.objects.get_or_create(
                    national_id=customer_data['national_id'],
                    defaults=customer_data
                )
                if created:
                    self.stdout.write(f"Created customer: {customer.first_name} {customer.last_name}")
        
        self.stdout.write(self.style.SUCCESS("Data migration completed successfully!"))
