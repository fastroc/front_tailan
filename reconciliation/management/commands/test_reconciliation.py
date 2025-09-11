from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from company.models import Company
from coa.models import Account
from bank_accounts.models import BankTransaction
from reconciliation.reconciliation_service import ReconciliationService
from reconciliation.models import TransactionMatch


class Command(BaseCommand):
    help = 'Test the reconciliation workflow'

    def handle(self, *args, **options):
        User = get_user_model()
        
        try:
            # Get test data
            user = User.objects.first()
            company = Company.objects.first()
            
            self.stdout.write(f"User: {user}")
            self.stdout.write(f"Company: {company}")
            
            # Get bank account (COA)
            bank_account = Account.objects.filter(
                company=company,
                account_type='Bank'
            ).first()
            
            if not bank_account:
                self.stdout.write(self.style.ERROR("No bank account found"))
                return
                
            self.stdout.write(f"Bank Account: {bank_account}")
            
            # Get unmatched transaction
            unmatched_transaction = BankTransaction.objects.filter(
                coa_account=bank_account
            ).exclude(
                id__in=TransactionMatch.objects.values_list('bank_transaction_id', flat=True)
            ).first()
            
            if not unmatched_transaction:
                self.stdout.write(self.style.ERROR("No unmatched transactions found"))
                return
                
            self.stdout.write(f"Test Transaction: {unmatched_transaction.description} - ${unmatched_transaction.amount}")
            
            # Get COA account for matching
            coa_account = Account.objects.filter(
                company=company,
                account_type__in=['REVENUE', 'EXPENSE', 'CURRENT_ASSET', 'LIABILITY']
            ).first()
            
            if not coa_account:
                self.stdout.write(self.style.ERROR("No COA account found"))
                return
                
            self.stdout.write(f"COA Account: {coa_account}")
            
            # Test reconciliation
            session = ReconciliationService.get_or_create_session(bank_account, user)
            self.stdout.write(f"Session: {session}")
            
            # Test transaction matching
            match_data = {
                'contact': 'Test Contact',
                'gl_account_id': coa_account.id,
                'description': 'Test reconciliation match',
                'tax_rate': 'no_gst'
            }
            
            match = ReconciliationService.match_transaction(
                bank_transaction=unmatched_transaction,
                reconciliation_session=session,
                match_data=match_data,
                user=user
            )
            
            if match:
                self.stdout.write(self.style.SUCCESS(f"Transaction matched successfully: {match.id}"))
                self.stdout.write(f"  Journal Entry: {match.journal_entry.id if match.journal_entry else 'None'}")
                
                if match.journal_entry:
                    self.stdout.write(f"  Journal Narration: {match.journal_entry.narration}")
                    self.stdout.write(f"  Journal Total: ${match.journal_entry.total_amount}")
                    
                # Test progress
                progress = ReconciliationService.get_reconciliation_progress(bank_account)
                self.stdout.write(f"Progress: {progress}")
                
                self.stdout.write(self.style.SUCCESS("✅ Reconciliation system working correctly!"))
            else:
                self.stdout.write(self.style.ERROR("❌ Transaction matching failed"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
