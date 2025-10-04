"""
Management command to calculate date ranges for all existing uploaded files
"""
from django.core.management.base import BaseCommand
from bank_accounts.models import UploadedFile


class Command(BaseCommand):
    help = 'Calculate date_from and date_to for all uploaded files based on their transactions'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Scanning uploaded files...\n')
        
        all_files = UploadedFile.objects.all()
        total_files = all_files.count()
        
        if total_files == 0:
            self.stdout.write(self.style.WARNING('No uploaded files found.'))
            return
        
        self.stdout.write(f'Found {total_files} uploaded files\n')
        
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        
        for i, upload_file in enumerate(all_files, 1):
            self.stdout.write(f'\n[{i}/{total_files}] Processing: {upload_file.original_filename}')
            self.stdout.write(f'   Account: {upload_file.account.name}')
            self.stdout.write(f'   Uploaded: {upload_file.uploaded_at}')
            
            try:
                # Try to calculate date range
                if upload_file.calculate_date_range():
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Calculated: {upload_file.date_from} to {upload_file.date_to} '
                        f'({upload_file.get_period_days()} days)'
                    ))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(
                        '   ⚠️  No transactions found for this file'
                    ))
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n✨ Done!'))
        self.stdout.write(f'\n📊 Summary:')
        self.stdout.write(f'   Total files: {total_files}')
        self.stdout.write(self.style.SUCCESS(f'   ✅ Updated: {updated_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'   ⚠️  Skipped (no transactions): {skipped_count}'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'   ❌ Failed: {failed_count}'))
