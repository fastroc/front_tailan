#!/usr/bin/env python
"""
Django management command to clean up orphaned bank transactions
Usage: python manage.py cleanup_orphaned_transactions
"""

from django.core.management.base import BaseCommand
from bank_accounts.models import BankTransaction, UploadedFile
from coa.models import Account


class Command(BaseCommand):
    help = 'Clean up orphaned bank transactions that have no corresponding upload file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('🔍 Checking for orphaned bank transactions...'))
        
        # Find all orphaned transactions
        all_transactions = BankTransaction.objects.all()
        orphaned = []
        
        for transaction in all_transactions:
            # Check if this transaction's upload file still exists
            upload_exists = UploadedFile.objects.filter(
                stored_filename=transaction.uploaded_file,
                account=transaction.coa_account
            ).exists()
            
            # Also check for transactions with empty uploaded_file field
            if not upload_exists or not transaction.uploaded_file:
                orphaned.append(transaction)
        
        if not orphaned:
            self.stdout.write(self.style.SUCCESS('✅ No orphaned transactions found!'))
            return
        
        self.stdout.write(f'Found {len(orphaned)} orphaned transactions:')
        
        # Group by account for better display
        by_account = {}
        for t in orphaned:
            account_name = t.coa_account.name
            if account_name not in by_account:
                by_account[account_name] = []
            by_account[account_name].append(t)
        
        for account_name, transactions in by_account.items():
            total_amount = sum(t.amount for t in transactions)
            self.stdout.write(f'  📊 {account_name}: {len(transactions)} transactions, total: ${total_amount}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No transactions were deleted'))
            return
        
        # Ask for confirmation unless --force is used
        if not force:
            confirm = input('\n⚠️  Delete these orphaned transactions? This cannot be undone! [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('❌ Operation cancelled')
                return
        
        # Delete orphaned transactions
        deleted_count = 0
        for transaction in orphaned:
            transaction.delete()
            deleted_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Deleted {deleted_count} orphaned transactions'))
        
        # Recalculate account balances
        self.stdout.write('🔄 Recalculating account balances...')
        accounts = Account.objects.filter(account_type='Bank')
        for account in accounts:
            remaining_transactions = BankTransaction.objects.filter(coa_account=account)
            new_balance = sum(t.amount for t in remaining_transactions)
            old_balance = account.current_balance
            
            if old_balance != new_balance:
                account.current_balance = new_balance
                account.save()
                self.stdout.write(f'  📈 {account.name}: ${old_balance} → ${new_balance}')
        
        self.stdout.write(self.style.SUCCESS('✅ Database cleanup completed!'))
