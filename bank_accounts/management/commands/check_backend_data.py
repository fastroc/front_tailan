from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.models import User
from bank_accounts.views import dashboard
from company.models import Company


class Command(BaseCommand):
    help = 'Show what data is passed to bank accounts templates'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== BANK ACCOUNTS BACKEND DATA ===\n'))
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/bank_accounts/')
        
        # Get a user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found'))
            return
            
        request.user = user
        request.session = {}
        
        # Test without company selected
        self.stdout.write("🔸 Testing without company selected:")
        response = dashboard(request)
        self.stdout.write(f"  Status Code: {response.status_code}")
        if hasattr(response, 'context_data'):
            context = response.context_data
            self.stdout.write(f"  Context keys: {list(context.keys()) if context else 'None'}")
        
        # Test with company selected
        company = Company.objects.first()
        if company:
            request.session['active_company_id'] = company.id
            self.stdout.write(f"\n🔸 Testing with company selected ({company.name}):")
            response = dashboard(request)
            self.stdout.write(f"  Status Code: {response.status_code}")
            if hasattr(response, 'context_data'):
                context = response.context_data
                self.stdout.write(f"  Context keys: {list(context.keys()) if context else 'None'}")
                if context and 'accounts' in context:
                    accounts = context['accounts']
                    self.stdout.write(f"  Accounts count: {len(accounts) if hasattr(accounts, '__len__') else 'Unknown'}")
                    if hasattr(accounts, 'count'):
                        self.stdout.write(f"  Accounts queryset count: {accounts.count()}")
                    if accounts:
                        self.stdout.write("  Account details:")
                        for account in accounts:
                            self.stdout.write(f"    - {account.name} (Code: {account.code or 'None'})")
                            self.stdout.write(f"      Balance: ${account.current_balance or 0}")
                            self.stdout.write(f"      Type: {account.account_type}")
        
        self.stdout.write(self.style.SUCCESS('\n=== END BACKEND DATA ==='))
