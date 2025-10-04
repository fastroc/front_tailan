import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from coa.models import Account
from django.db.models import Count

print("=" * 80)
print("🔍 SEARCHING FOR DUPLICATE ACCOUNT CODES")
print("=" * 80)

# Find duplicates
duplicates = Account.objects.values('company_id', 'code').annotate(
    count=Count('id')
).filter(count__gt=1).order_by('-count')

print(f"\n📊 Found {duplicates.count()} duplicate code groups\n")

if duplicates.count() == 0:
    print("✅ No duplicates found!")
else:
    for dup in duplicates:
        print(f"\n🔴 DUPLICATE: Company {dup['company_id']} | Code '{dup['code']}' | Count: {dup['count']}")
        
        # Get all accounts with this duplicate code
        accounts = Account.objects.filter(
            company_id=dup['company_id'], 
            code=dup['code']
        ).order_by('id')
        
        for acc in accounts:
            print(f"   ID {acc.id:4d} | {acc.code} - {acc.name[:50]:50s} | Active: {acc.is_active} | YTD: ${acc.ytd_balance:12,.2f}")

print("\n" + "=" * 80)

# Specifically check code 6127
print("\n🔍 SPECIFICALLY CHECKING CODE 6127:")
code_6127 = Account.objects.filter(code='6127')
print(f"Found {code_6127.count()} accounts with code 6127:")
for acc in code_6127:
    print(f"   ID {acc.id} | Company {acc.company_id} | {acc.code} - {acc.name} | Active: {acc.is_active}")
