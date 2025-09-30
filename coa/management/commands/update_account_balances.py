#!/usr/bin/env python3

from django.core.management.base import BaseCommand
from django.db import transaction
from coa.models import Account
from company.models import Company
from journal.models import Journal, JournalLine


class Command(BaseCommand):
    help = 'Update Chart of Accounts balances from posted journal entries'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Update balances for specific company only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each account',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔄 Starting Chart of Accounts balance update...\n')
        
        # Get company filter
        company = None
        if options['company_id']:
            try:
                company = Company.objects.get(id=options['company_id'])
                self.stdout.write(f'📊 Updating balances for company: {company.name}')
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Company with ID {options["company_id"]} not found')
                )
                return
        else:
            self.stdout.write('📊 Updating balances for all companies')
        
        # Get accounts to update
        accounts = Account.objects.filter(is_active=True)
        if company:
            accounts = accounts.filter(company=company)
            
        total_accounts = accounts.count()
        self.stdout.write(f'📋 Found {total_accounts} active accounts to process\n')
        
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for account in accounts:
                try:
                    old_balance = account.current_balance
                    
                    if options['dry_run']:
                        # Calculate new balance without saving
                        new_balance = self._calculate_balance_for_account(account)
                    else:
                        # Update balance
                        new_balance = account.update_balance_from_journals()
                    
                    balance_changed = abs(old_balance - new_balance) > 0.01
                    
                    if balance_changed:
                        updated_count += 1
                        status_icon = '🔄' if options['dry_run'] else '✅'
                        action = 'Would update' if options['dry_run'] else 'Updated'
                        
                        self.stdout.write(
                            f'{status_icon} {action}: {account.code} - {account.name}'
                        )
                        self.stdout.write(
                            f'   Old: ${old_balance:,.2f} → New: ${new_balance:,.2f} '
                            f'(Change: ${new_balance - old_balance:,.2f})'
                        )
                        
                        if options['verbose']:
                            self._show_account_journal_summary(account)
                        
                    elif options['verbose']:
                        self.stdout.write(
                            f'⏸️  No change: {account.code} - {account.name} (${old_balance:,.2f})'
                        )
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ Error updating {account.code}: {str(e)}'
                        )
                    )
        
        # Summary
        self.stdout.write('\n📈 === UPDATE SUMMARY ===')
        if options['dry_run']:
            self.stdout.write(f'🔍 DRY RUN: {updated_count} accounts would be updated')
        else:
            self.stdout.write(f'✅ Updated: {updated_count} accounts')
            
        self.stdout.write(f'⏸️  Unchanged: {total_accounts - updated_count - error_count} accounts')
        
        if error_count > 0:
            self.stdout.write(f'❌ Errors: {error_count} accounts')
            
        self.stdout.write('\n🎯 Balance update complete!')
        
        if options['dry_run']:
            self.stdout.write('💡 Run without --dry-run to apply changes')
    
    def _calculate_balance_for_account(self, account):
        """Calculate balance for account without saving"""
        journal_lines = JournalLine.objects.filter(
            account_code=account.code,
            company=account.company,
            journal__status='posted'
        )
        
        total_debits = sum(line.debit for line in journal_lines)
        total_credits = sum(line.credit for line in journal_lines)
        
        # Calculate net balance based on account type
        if account.account_type in ['CURRENT_ASSET', 'FIXED_ASSET', 'INVENTORY', 
                                   'NON_CURRENT_ASSET', 'PREPAYMENT', 'DIRECT_COST', 
                                   'OVERHEAD', 'DEPRECIATION']:
            net_balance = total_debits - total_credits
        else:
            net_balance = total_credits - total_debits
        
        return account.opening_balance + net_balance
    
    def _show_account_journal_summary(self, account):
        """Show summary of journal entries for account"""
        journal_lines = JournalLine.objects.filter(
            account_code=account.code,
            company=account.company,
            journal__status='posted'
        ).select_related('journal')
        
        if journal_lines.exists():
            total_debits = sum(line.debit for line in journal_lines)
            total_credits = sum(line.credit for line in journal_lines)
            
            self.stdout.write(f'     Journal Activity:')
            self.stdout.write(f'       • {journal_lines.count()} journal lines')
            self.stdout.write(f'       • Total Debits: ${total_debits:,.2f}')
            self.stdout.write(f'       • Total Credits: ${total_credits:,.2f}')
            self.stdout.write(f'       • Opening Balance: ${account.opening_balance:,.2f}')
        else:
            self.stdout.write(f'     No journal entries found')
