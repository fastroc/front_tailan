#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

print('=== VERIFYING RECONCILIATION TABLES ===')

# Check if reconciliation tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'reconciliation%'")
tables = cursor.fetchall()
print('Reconciliation tables:')
for table in tables:
    print(f'  - {table[0]}')

if tables:
    # Test importing reconciliation models
    try:
        from reconciliation.models import ReconciliationSession, TransactionMatch, ReconciliationReport
        print(f'\nReconciliationSession count: {ReconciliationSession.objects.count()}')
        print(f'TransactionMatch count: {TransactionMatch.objects.count()}')  
        print(f'ReconciliationReport count: {ReconciliationReport.objects.count()}')
        print('\n✅ Reconciliation models working!')
    except Exception as e:
        print(f'\n❌ Error with reconciliation models: {e}')
else:
    print('\n❌ No reconciliation tables found!')
