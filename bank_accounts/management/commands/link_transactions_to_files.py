"""
Management command to link existing transactions to their uploaded files
"""
from django.core.management.base import BaseCommand
from bank_accounts.models import BankTransaction, UploadedFile
from django.db.models import Count


class Command(BaseCommand):
    help = 'Link existing transactions to their uploaded files based on upload timestamps'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Scanning for unlinked transactions...\n')
        
        # Get all transactions with empty uploaded_file field
        unlinked_txns = BankTransaction.objects.filter(uploaded_file='')
        total_unlinked = unlinked_txns.count()
        
        if total_unlinked == 0:
            self.stdout.write(self.style.SUCCESS('✅ All transactions are already linked!'))
            return
        
        self.stdout.write(f'Found {total_unlinked} unlinked transactions\n')
        
        # Get all uploaded files
        uploaded_files = UploadedFile.objects.all().order_by('uploaded_at')
        
        self.stdout.write(f'Found {uploaded_files.count()} uploaded files\n')
        
        updated_count = 0
        
        for upload_file in uploaded_files:
            self.stdout.write(f'\n📁 Processing: {upload_file.original_filename}')
            self.stdout.write(f'   Uploaded at: {upload_file.uploaded_at}')
            self.stdout.write(f'   Account: {upload_file.account.name}')
            
            # Find transactions uploaded around the same time for this account
            # Use a time window: transactions created within 5 minutes of file upload
            from datetime import timedelta
            time_window_start = upload_file.uploaded_at - timedelta(minutes=5)
            time_window_end = upload_file.uploaded_at + timedelta(minutes=5)
            
            matching_txns = BankTransaction.objects.filter(
                coa_account=upload_file.account,
                uploaded_file='',  # Only unlinked transactions
                uploaded_at__gte=time_window_start,
                uploaded_at__lte=time_window_end
            )
            
            count = matching_txns.count()
            
            if count > 0:
                # Update these transactions
                matching_txns.update(uploaded_file=upload_file.stored_filename)
                updated_count += count
                self.stdout.write(self.style.SUCCESS(f'   ✅ Linked {count} transactions'))
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠️  No matching transactions found'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✨ Done! Updated {updated_count} transactions'))
        
        # Show remaining unlinked
        remaining = BankTransaction.objects.filter(uploaded_file='').count()
        if remaining > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {remaining} transactions remain unlinked'))
        else:
            self.stdout.write(self.style.SUCCESS('🎉 All transactions are now linked!'))
