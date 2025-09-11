#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Remove migration record
cursor.execute("DELETE FROM django_migrations WHERE app='reconciliation'")
print(f"Deleted {cursor.rowcount} migration records for reconciliation")

# Check current migration state
cursor.execute("SELECT * FROM django_migrations WHERE app='reconciliation'")
remaining = cursor.fetchall()
print(f"Remaining reconciliation migration records: {len(remaining)}")
