"""
Reconciliation Services
Handles the business logic for transaction matching and auto journal creation
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import ReconciliationSession, TransactionMatch
from bank_accounts.models import BankTransaction
from journal.models import Journal, JournalLine
from coa.models import Account


class ReconciliationService:
    """Service class for handling reconciliation operations"""
    
    @classmethod
    def get_or_create_session(cls, account, user):
        """Get or create a reconciliation session for an account"""
        # Check if there's an active session
        active_session = ReconciliationSession.objects.filter(
            account=account,
            status='in_progress'
        ).first()
        
        if active_session:
            return active_session
            
        # Create new session
        session = ReconciliationSession.objects.create(
            account=account,
            session_name=f"Reconciliation - {timezone.now().strftime('%Y-%m-%d')}",
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            created_by=user,
            status='in_progress'
        )
        
        # Update session statistics
        cls.update_session_statistics(session)
        return session
    
    @classmethod 
    def get_unmatched_transactions(cls, account):
        """Get all unmatched transactions for an account"""
        matched_transaction_ids = TransactionMatch.objects.filter(
            bank_transaction__coa_account=account
        ).values_list('bank_transaction_id', flat=True)
        
        return BankTransaction.objects.filter(
            coa_account=account
        ).exclude(
            id__in=matched_transaction_ids
        ).order_by('-date', '-id')
    
    @classmethod
    @transaction.atomic
    def match_transaction(cls, bank_transaction, reconciliation_session, match_data, user):
        """
        Match a bank transaction with WHO/WHAT/WHY/TAX data
        
        Args:
            bank_transaction: BankTransaction instance
            reconciliation_session: ReconciliationSession instance
            match_data: dict with 'contact', 'gl_account_id', 'description', 'tax_rate'
            user: User making the match
        """
        
        # Create transaction match
        transaction_match = TransactionMatch.objects.create(
            bank_transaction=bank_transaction,
            reconciliation_session=reconciliation_session,
            contact=match_data.get('contact', ''),
            gl_account_id=match_data.get('gl_account_id'),
            description=match_data.get('description', ''),
            tax_rate=match_data.get('tax_rate', ''),
            match_type='manual',
            matched_by=user,
            matched_at=timezone.now(),
            is_reconciled=True
        )
        
        # Auto-create journal entry
        journal_entry = cls.create_journal_from_match(transaction_match, user)
        transaction_match.journal_entry = journal_entry
        transaction_match.save()
        
        # Update session statistics
        cls.update_session_statistics(reconciliation_session)
        
        return transaction_match
    
    @classmethod
    def create_journal_from_match(cls, transaction_match, user):
        """Auto-create journal entry from transaction match"""
        bank_txn = transaction_match.bank_transaction
        gl_account = transaction_match.gl_account
        
        if not gl_account:
            return None
            
        # Create journal entry
        journal = Journal.objects.create(
            narration=f"Bank: {transaction_match.description or bank_txn.description}",
            reference=bank_txn.reference,
            date=bank_txn.date,
            created_by=user,
            status='posted'  # Auto-post reconciliation entries
        )
        
        # Determine if this is income (credit GL, debit bank) or expense (debit GL, credit bank)
        amount = abs(bank_txn.amount)
        
        if bank_txn.amount > 0:
            # Money coming IN (income): Credit GL account, Debit Bank account
            # GL Account (Credit)
            JournalLine.objects.create(
                journal=journal,
                description=transaction_match.description or bank_txn.description,
                account_code=gl_account.code,
                credit=amount,
                debit=0
            )
            
            # Bank Account (Debit)
            JournalLine.objects.create(
                journal=journal,
                description=f"Bank deposit - {transaction_match.contact}",
                account_code=bank_txn.coa_account.code,
                debit=amount,
                credit=0
            )
        else:
            # Money going OUT (expense): Debit GL account, Credit Bank account
            # GL Account (Debit)
            JournalLine.objects.create(
                journal=journal,
                description=transaction_match.description or bank_txn.description,
                account_code=gl_account.code,
                debit=amount,
                credit=0
            )
            
            # Bank Account (Credit)
            JournalLine.objects.create(
                journal=journal,
                description=f"Bank payment - {transaction_match.contact}",
                account_code=bank_txn.coa_account.code,
                credit=amount,
                debit=0
            )
        
        return journal
    
    @classmethod
    def update_session_statistics(cls, session):
        """Update reconciliation session statistics"""
        # Total transactions for this account
        total_transactions = BankTransaction.objects.filter(
            coa_account=session.account
        ).count()
        
        # Matched transactions
        matched_transactions = TransactionMatch.objects.filter(
            reconciliation_session=session,
            is_reconciled=True
        ).count()
        
        # Update session
        session.total_transactions = total_transactions
        session.matched_transactions = matched_transactions
        session.unmatched_transactions = total_transactions - matched_transactions
        session.save()
        
        return session
    
    @classmethod
    def get_reconciliation_progress(cls, account):
        """Get reconciliation progress for an account"""
        total_transactions = BankTransaction.objects.filter(coa_account=account).count()
        matched_transactions = TransactionMatch.objects.filter(
            bank_transaction__coa_account=account,
            is_reconciled=True
        ).count()
        
        percentage = 0
        if total_transactions > 0:
            percentage = round((matched_transactions / total_transactions) * 100, 1)
            
        return {
            'total_transactions': total_transactions,
            'matched_transactions': matched_transactions,
            'unmatched_transactions': total_transactions - matched_transactions,
            'percentage': percentage
        }
