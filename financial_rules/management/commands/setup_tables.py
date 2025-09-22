"""
Create financial rules tables using Django schema editor
"""
from django.core.management.base import BaseCommand
from django.db import connection
from financial_rules.models import BaseFinancialRule, RuleCondition, RuleAction, RuleExecutionLog


class Command(BaseCommand):
    help = 'Create financial rules tables using Django schema editor'

    def handle(self, *args, **options):
        self.stdout.write("Creating financial rules tables...")
        
        from django.db import connection
        from django.core.management.sql import sql_create_index
        from django.db.backends.utils import names_digest
        
        # Use Django's schema editor to create tables
        with connection.schema_editor() as schema_editor:
            try:
                # Create tables for all models
                models = [BaseFinancialRule, RuleCondition, RuleAction, RuleExecutionLog]
                
                for model in models:
                    self.stdout.write(f"Creating table for {model.__name__}...")
                    try:
                        schema_editor.create_model(model)
                        self.stdout.write(f"✅ Created table for {model.__name__}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            self.stdout.write(f"⚠️ Table for {model.__name__} already exists")
                        else:
                            self.stdout.write(f"❌ Failed to create table for {model.__name__}: {e}")
                
                self.stdout.write("✅ Financial rules tables created successfully!")
                
                # Now populate with demo data
                self.stdout.write("Creating demo data...")
                from django.core.management import call_command
                call_command('create_demo_data')
                
            except Exception as e:
                self.stdout.write(f"❌ Error creating tables: {e}")
                raise
