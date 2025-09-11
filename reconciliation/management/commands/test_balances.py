from django.core.management.base import BaseCommand
from reconciliation.reconciliation_service import ReconciliationService
from coa.models import Account
from company.models import Company


class Command(BaseCommand):
    help = 'Test the updated balance calculations'

    def handle(self, *args, **options):
        try:
            company = Company.objects.first()
            account = Account.objects.filter(company=company, account_type='Bank').first()
            
            if not account:
                self.stdout.write(self.style.ERROR("No bank account found"))
                return
                
            progress = ReconciliationService.get_reconciliation_progress(account)
            
            self.stdout.write(f"🏦 Account: {account.name}")
            self.stdout.write(f"📊 Statement Balance: ${progress['statement_balance']:,.2f}")
            self.stdout.write(f"✅ Reconciled Balance: ${progress['reconciled_balance']:,.2f}")
            self.stdout.write(f"⚖️  Remaining: ${progress['difference']:,.2f}")
            self.stdout.write(f"📈 Progress: {progress['matched_transactions']}/{progress['total_transactions']} ({progress['percentage']}%)")
            
            if progress['difference'] == 0:
                self.stdout.write(self.style.SUCCESS("🎉 Account is fully reconciled!"))
            else:
                remaining_percentage = ((progress['difference'] / progress['statement_balance']) * 100) if progress['statement_balance'] != 0 else 0
                self.stdout.write(f"⏳ {remaining_percentage:.1f}% of statement balance remaining to reconcile")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
