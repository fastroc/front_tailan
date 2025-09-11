"""
Django Management Command: Auto-register admin models
Automatically registers all models for enhanced admin interface
"""
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Automatically register all models in Django admin with enhanced interfaces'

    def handle(self, *args, **options):
        if not getattr(settings, 'DEBUG', False):
            self.stdout.write(
                self.style.WARNING('Admin auto-registration is only available in DEBUG mode')
            )
            return

        try:
            # Import the automation system
            from core.admin_automation import auto_register_all_models, configure_admin_site
            
            self.stdout.write('🤖 Starting automated admin registration...')
            
            # Run the automation
            auto_register_all_models()
            configure_admin_site()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Admin automation completed successfully!')
            )
            self.stdout.write(
                self.style.SUCCESS('🎯 All database models now visible in admin at /admin/')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during admin automation: {e}')
            )
