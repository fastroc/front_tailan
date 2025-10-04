import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from coa.models import Account

print('🔗 DIRECT DELETE URLS FOR YOUR ACCOUNTS')
print('='*80)
print()
print('Copy-paste these URLs into your browser to delete accounts directly:')
print()

inactive_accounts = Account.objects.filter(is_active=False)

if inactive_accounts.exists():
    print(f'📋 Found {inactive_accounts.count()} INACTIVE accounts:')
    print()
    for account in inactive_accounts:
        can_delete = account.can_be_deleted()
        url = f'http://localhost:8000/coa/account/{account.id}/delete/'
        
        if can_delete:
            print(f'✅ CAN DELETE:')
            print(f'   Account: {account.code} - {account.name}')
            print(f'   URL: {url}')
            print()
        else:
            print(f'❌ CANNOT DELETE:')
            print(f'   Account: {account.code} - {account.name}')
            if account.is_locked:
                print(f'   Reason: Account is LOCKED')
            elif account.get_children().exists():
                print(f'   Reason: Has {account.get_children().count()} child accounts')
            print()
else:
    print('ℹ️  No inactive accounts found')
    print()

# Also show some active accounts
print('='*80)
print()
print('📋 First 10 ACTIVE accounts (for testing):')
print()

active_accounts = Account.objects.filter(is_active=True)[:10]
for account in active_accounts:
    can_delete = account.can_be_deleted()
    url = f'http://localhost:8000/coa/account/{account.id}/delete/'
    
    status = '✅' if can_delete else '❌'
    print(f'{status} {account.code} - {account.name[:50]}')
    print(f'   URL: {url}')
    print()

print('='*80)
print()
print('💡 HOW TO USE:')
print('   1. Copy a URL from above')
print('   2. Paste into browser address bar')
print('   3. Press Enter')
print('   4. Confirm deletion')
print('   5. Done! ✅')
