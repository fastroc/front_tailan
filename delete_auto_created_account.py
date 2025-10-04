import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from coa.models import Account

print("=" * 80)
print("🗑️ DELETING AUTO-CREATED ACCOUNT")
print("=" * 80)

try:
    acc = Account.objects.get(code='6118')
    print(f"\nFound: ID {acc.id} | {acc.code} - {acc.name}")
    print(f"Company: {acc.company.name}")
    print(f"Account Type: {acc.account_type}")
    
    # Check for related data
    match_count = acc.transactionmatch_set.count()
    print(f"Transaction Matches: {match_count}")
    
    if match_count > 0:
        print("\n⚠️ WARNING: This account has transaction matches!")
        print("Are you sure you want to delete? (This will also delete the matches)")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            exit()
    
    acc.delete()
    print("\n✅ Account deleted successfully!")
    
except Account.DoesNotExist:
    print("\n❌ Account with code 6118 not found")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("=" * 80)
