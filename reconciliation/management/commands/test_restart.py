from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from company.models import Company
from coa.models import Account
from bank_accounts.models import BankTransaction
from reconciliation.reconciliation_service import ReconciliationService
from reconciliation.models import TransactionMatch


class Command(BaseCommand):
    help = 'Test the restart reconciliation functionality'

    def handle(self, *args, **options):
        User = get_user_model()
        
        try:
            # Get test data
            user = User.objects.first()
            company = Company.objects.first()
            
            # Get bank account
            bank_account = Account.objects.filter(
                company=company,
                account_type='Bank'
            ).first()
            
            if not bank_account:
                self.stdout.write(self.style.ERROR("No bank account found"))
                return
                
            self.stdout.write(f"Testing restart for: {bank_account.name}")
            
            # Check current matches
            current_matches = TransactionMatch.objects.filter(
                reconciliation_session__account=bank_account
            ).count()
            
            self.stdout.write(f"Current matches before restart: {current_matches}")
            
            if current_matches == 0:
                self.stdout.write(self.style.WARNING("No matches to restart - creating a test match first"))
                
                # Create a test match
                unmatched_transaction = BankTransaction.objects.filter(
                    coa_account=bank_account
                ).exclude(
                    id__in=TransactionMatch.objects.values_list('bank_transaction_id', flat=True)
                ).first()
                
                if unmatched_transaction:
                    # Get COA account
                    coa_account = Account.objects.filter(
                        company=company,
                        account_type__in=['REVENUE', 'EXPENSE', 'CURRENT_ASSET', 'LIABILITY']
                    ).first()
                    
                    if coa_account:
                        session = ReconciliationService.get_or_create_session(bank_account, user)
                        match_data = {
                            'contact': 'Test Contact',
                            'gl_account_id': coa_account.id,
                            'description': 'Test match for restart testing',
                            'tax_rate': 'no_gst'
                        }
                        
                        match = ReconciliationService.match_transaction(
                            bank_transaction=unmatched_transaction,
                            reconciliation_session=session,
                            match_data=match_data,
                            user=user
                        )
                        
                        if match:
                            self.stdout.write(self.style.SUCCESS("Created test match for restart testing"))
                        else:
                            self.stdout.write(self.style.ERROR("Failed to create test match"))
                            return
            
            # Test restart functionality
            self.stdout.write("\n🔄 Testing restart reconciliation...")
            
            result = ReconciliationService.restart_reconciliation(
                account=bank_account,
                user=user,
                delete_journal_entries=False
            )
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"✅ {result['message']}"))
                self.stdout.write(f"   Matches deleted: {result['matches_deleted']}")
                self.stdout.write(f"   Journals deleted: {result['journals_deleted']}")
                
                # Verify matches are deleted
                remaining_matches = TransactionMatch.objects.filter(
                    reconciliation_session__account=bank_account
                ).count()
                
                if remaining_matches == 0:
                    self.stdout.write(self.style.SUCCESS("✅ All matches successfully deleted"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Still have {remaining_matches} matches remaining"))
                
                # Check session status
                session = ReconciliationService.get_or_create_session(bank_account, user)
                progress = ReconciliationService.get_reconciliation_progress(bank_account)
                
                self.stdout.write(f"   Session status: {session.status}")
                self.stdout.write(f"   Progress: {progress['matched_transactions']}/{progress['total_transactions']} matched")
                
            else:
                self.stdout.write(self.style.ERROR(f"❌ {result['message']}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
