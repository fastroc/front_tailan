from django.core.management.base import BaseCommand
from django.db import transaction
from loans_customers.models import Customer, CustomerDocument
from loans_core.models import LoanApplication, Loan
from loans_schedule.models import PaymentSchedule, ScheduledPayment
from company.models import Company


class Command(BaseCommand):
    help = 'Clear all customers, loan applications, and related data for a fresh start'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Clear data for specific company ID only',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without interactive prompt',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  WARNING: This will DELETE ALL customer and loan data!'))
        
        # Get companies to clear data for
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
            self.stdout.write(self.style.ERROR('No companies found.'))
            return

        # Show what will be deleted
        total_customers = 0
        total_applications = 0
        total_loans = 0
        total_schedules = 0
        total_documents = 0

        for company in companies:
            customers = Customer.objects.filter(company=company)
            applications = LoanApplication.objects.filter(company=company)
            loans = Loan.objects.filter(company=company)
            schedules = PaymentSchedule.objects.filter(company=company)
            documents = CustomerDocument.objects.filter(company=company)
            
            total_customers += customers.count()
            total_applications += applications.count()
            total_loans += loans.count()
            total_schedules += schedules.count()
            total_documents += documents.count()
            
            self.stdout.write(f'\n🏢 {company.name}:')
            self.stdout.write(f'  👥 Customers: {customers.count()}')
            self.stdout.write(f'  📋 Applications: {applications.count()}')
            self.stdout.write(f'  💰 Loans: {loans.count()}')
            self.stdout.write(f'  📅 Payment Schedules: {schedules.count()}')
            self.stdout.write(f'  📄 Documents: {documents.count()}')

        self.stdout.write('\n📊 TOTAL ACROSS ALL COMPANIES:')
        self.stdout.write(f'  👥 Customers: {total_customers}')
        self.stdout.write(f'  📋 Applications: {total_applications}')
        self.stdout.write(f'  💰 Loans: {total_loans}')
        self.stdout.write(f'  📅 Payment Schedules: {total_schedules}')
        self.stdout.write(f'  📄 Documents: {total_documents}')

        if total_customers == 0 and total_applications == 0 and total_loans == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No data to clear - already clean!'))
            return

        # Confirmation
        if not options['confirm']:
            confirm = input('\n❓ Are you sure you want to DELETE all this data? Type "DELETE ALL" to confirm: ')
            if confirm != "DELETE ALL":
                self.stdout.write(self.style.WARNING('❌ Operation cancelled.'))
                return

        # Delete data in correct order (foreign key dependencies)
        deleted_counts = {
            'scheduled_payments': 0,
            'payment_schedules': 0,
            'loans': 0,
            'applications': 0,
            'documents': 0,
            'customers': 0,
        }

        with transaction.atomic():
            for company in companies:
                self.stdout.write(f'\n🧹 Cleaning {company.name}...')
                
                # 1. Delete scheduled payments first
                scheduled_payments = ScheduledPayment.objects.filter(company=company)
                count = scheduled_payments.count()
                if count > 0:
                    scheduled_payments.delete()
                    deleted_counts['scheduled_payments'] += count
                    self.stdout.write(f'  ✅ Deleted {count} scheduled payments')

                # 2. Delete payment schedules
                payment_schedules = PaymentSchedule.objects.filter(company=company)
                count = payment_schedules.count()
                if count > 0:
                    payment_schedules.delete()
                    deleted_counts['payment_schedules'] += count
                    self.stdout.write(f'  ✅ Deleted {count} payment schedules')

                # 3. Delete loans
                loans = Loan.objects.filter(company=company)
                count = loans.count()
                if count > 0:
                    loans.delete()
                    deleted_counts['loans'] += count
                    self.stdout.write(f'  ✅ Deleted {count} loans')

                # 4. Delete loan applications
                applications = LoanApplication.objects.filter(company=company)
                count = applications.count()
                if count > 0:
                    applications.delete()
                    deleted_counts['applications'] += count
                    self.stdout.write(f'  ✅ Deleted {count} applications')

                # 5. Delete customer documents
                documents = CustomerDocument.objects.filter(company=company)
                count = documents.count()
                if count > 0:
                    documents.delete()
                    deleted_counts['documents'] += count
                    self.stdout.write(f'  ✅ Deleted {count} customer documents')

                # 6. Delete customers last
                customers = Customer.objects.filter(company=company)
                count = customers.count()
                if count > 0:
                    customers.delete()
                    deleted_counts['customers'] += count
                    self.stdout.write(f'  ✅ Deleted {count} customers')

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🎉 CLEANUP COMPLETE!'))
        self.stdout.write('📊 Total Deleted:')
        self.stdout.write(f'  👥 Customers: {deleted_counts["customers"]}')
        self.stdout.write(f'  📋 Applications: {deleted_counts["applications"]}')
        self.stdout.write(f'  💰 Loans: {deleted_counts["loans"]}')
        self.stdout.write(f'  📅 Payment Schedules: {deleted_counts["payment_schedules"]}')
        self.stdout.write(f'  🗓️ Scheduled Payments: {deleted_counts["scheduled_payments"]}')
        self.stdout.write(f'  📄 Documents: {deleted_counts["documents"]}')
        self.stdout.write(self.style.SUCCESS('\n✨ Database is now clean - ready for fresh start!'))
