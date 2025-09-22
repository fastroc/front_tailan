"""
Test migration command
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Test database connection and run migrations'

    def handle(self, *args, **options):
        self.stdout.write("Testing database connection...")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.stdout.write(f"✅ Database connection successful: {result}")
        except Exception as e:
            self.stdout.write(f"❌ Database connection failed: {e}")
            return
            
        self.stdout.write("Running migrations...")
        
        from django.core.management import call_command
        try:
            call_command('migrate', 'financial_rules', verbosity=2)
            self.stdout.write("✅ Migrations completed successfully")
        except Exception as e:
            self.stdout.write(f"❌ Migration failed: {e}")
            # Try to create tables manually
            self.create_tables_manually()
    
    def create_tables_manually(self):
        self.stdout.write("Attempting to create tables manually...")
        
        with connection.cursor() as cursor:
            try:
                # Create the financial_rules_basefinancialrule table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS financial_rules_basefinancialrule (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        rule_type VARCHAR(50) NOT NULL,
                        priority INTEGER DEFAULT 100,
                        is_active BOOLEAN DEFAULT 1,
                        condition_logic VARCHAR(10) DEFAULT 'and',
                        usage_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        company_id INTEGER NOT NULL REFERENCES company_company(id)
                    )
                ''')
                
                # Create the financial_rules_rulecondition table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS financial_rules_rulecondition (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        field VARCHAR(50) NOT NULL,
                        operator VARCHAR(20) NOT NULL,
                        value VARCHAR(255) NOT NULL,
                        case_sensitive BOOLEAN DEFAULT 0,
                        rule_id INTEGER NOT NULL REFERENCES financial_rules_basefinancialrule(id)
                    )
                ''')
                
                # Create the financial_rules_ruleaction table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS financial_rules_ruleaction (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_type VARCHAR(50) NOT NULL,
                        target_account VARCHAR(100) NOT NULL,
                        amount DECIMAL(15,2),
                        percentage DECIMAL(5,2),
                        parameters TEXT DEFAULT '{}',
                        rule_id INTEGER NOT NULL REFERENCES financial_rules_basefinancialrule(id)
                    )
                ''')
                
                # Create the financial_rules_ruleexecutionlog table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS financial_rules_ruleexecutionlog (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        input_data TEXT NOT NULL,
                        output_data TEXT,
                        success BOOLEAN DEFAULT 1,
                        error_message TEXT,
                        execution_time_ms INTEGER,
                        rule_id INTEGER NOT NULL REFERENCES financial_rules_basefinancialrule(id)
                    )
                ''')
                
                self.stdout.write("✅ Tables created manually")
                
            except Exception as e:
                self.stdout.write(f"❌ Manual table creation failed: {e}")
