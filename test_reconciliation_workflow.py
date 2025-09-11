#!/usr/bin/env python
"""
Comprehensive test for the reconciliation system workflow
This script tests the complete transaction matching process.
"""

import os
import sys
import django
import json
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from company.models import Company
from bank_accounts.models import BankTransaction
from coa.models import Account
from reconciliation.models import TransactionMatch
from reconciliation.reconciliation_service import ReconciliationService

User = get_user_model()

def test_reconciliation_workflow():
    """Test complete reconciliation workflow"""
    print("🔄 Testing Complete Reconciliation Workflow")
    print("=" * 50)
    
    try:
        # Get test data
        user = User.objects.first()
        if not user:
            print("❌ No user found")
            return False
            
        company = Company.objects.first()
        if not company:
            print("❌ No company found")
            return False
            
        # Get test bank account (from COA)
        bank_account = Account.objects.filter(
            company=company,
            account_type='Bank'
        ).first()
        if not bank_account:
            print("❌ No bank account found")
            return False
            
        # Get first unmatched transaction
        unmatched_transaction = BankTransaction.objects.filter(
            coa_account=bank_account
        ).exclude(
            id__in=TransactionMatch.objects.values_list('bank_transaction_id', flat=True)
        ).first()
        
        if not unmatched_transaction:
            print("❌ No unmatched transactions found")
            return False
            
        print(f"✅ Found test transaction: {unmatched_transaction.description}")
        print(f"   Amount: ${unmatched_transaction.amount}")
        print(f"   Date: {unmatched_transaction.date}")
        
        # Get a chart of accounts entry
        coa_account = Account.objects.filter(
            company=company,
            account_type__in=['REVENUE', 'EXPENSE', 'CURRENT_ASSET', 'LIABILITY']
        ).first()
        
        if not coa_account:
            print("❌ No chart of accounts entries found")
            return False
            
        print(f"✅ Using COA Account: {coa_account.name}")
        
        # Test 1: Get or create reconciliation session
        print("\n📋 Step 1: Getting reconciliation session...")
        session = ReconciliationService.get_or_create_session(bank_account, user)
        print(f"✅ Session created/retrieved: {session.id}")
        print(f"   Period: {session.period_start} to {session.period_end}")
        print(f"   Status: {session.status}")
        
        # Test 2: Test transaction matching
        print("\n🔗 Step 2: Testing transaction matching...")
        match_data = {
            'contact': 'Test Contact',
            'gl_account_id': coa_account.id,
            'description': 'Test reconciliation match',
            'tax_rate': 'no_gst'
        }
        
        initial_matches = TransactionMatch.objects.count()
        
        try:
            match = ReconciliationService.match_transaction(
                bank_transaction=unmatched_transaction,
                reconciliation_session=session,
                match_data=match_data,
                user=user
            )
            
            if match:
                print(f"✅ Transaction matched successfully: {match.id}")
                print(f"   Contact: {match.contact}")
                print(f"   Description: {match.description}")
                print(f"   Tax Rate: {match.tax_rate}")
                print(f"   Journal Entry: {match.journal_entry.id if match.journal_entry else 'None'}")
                
                # Verify journal entry was created
                if match.journal_entry:
                    print(f"   Journal Narration: {match.journal_entry.narration}")
                    print(f"   Journal Total Amount: ${match.journal_entry.total_amount}")
                else:
                    print("⚠️  Warning: No journal entry created")
                    
            else:
                print("❌ Transaction matching failed")
                return False
                
        except Exception as e:
            print(f"❌ Error during transaction matching: {str(e)}")
            return False
        
        # Test 3: Check session statistics
        print("\n📊 Step 3: Checking session statistics...")
        progress = ReconciliationService.get_reconciliation_progress(bank_account)
        
        print(f"✅ Reconciliation Progress:")
        print(f"   Total Transactions: {progress.get('total_transactions', 0)}")
        print(f"   Matched Transactions: {progress.get('matched_transactions', 0)}")
        print(f"   Unmatched Transactions: {progress.get('unmatched_transactions', 0)}")
        print(f"   Balance: ${progress.get('balance', 0)}")
        print(f"   Statement Balance: ${progress.get('statement_balance', 0)}")
        print(f"   Difference: ${progress.get('difference', 0)}")
        
        # Test 4: Test AJAX endpoint simulation
        print("\n🌐 Step 4: Testing AJAX endpoint simulation...")
        client = Client()
        
        # Login first
        client.force_login(user)
        
        # Set active company in session
        session_data = client.session
        session_data['active_company_id'] = company.id
        session_data.save()
        
        # Get another unmatched transaction for AJAX test
        ajax_transaction = BankTransaction.objects.filter(
            coa_account=bank_account
        ).exclude(
            id__in=TransactionMatch.objects.values_list('bank_transaction_id', flat=True)
        ).first()
        
        if ajax_transaction:
            ajax_data = {
                'transaction_id': ajax_transaction.id,
                'contact': 'AJAX Test Contact',
                'account_id': coa_account.id,
                'tax_treatment': 'no_gst',
                'notes': 'AJAX test transaction match'
            }
            
            response = client.post(
                '/reconciliation/ajax/match_transaction/',
                data=json.dumps(ajax_data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                result = json.loads(response.content)
                if result.get('success'):
                    print(f"✅ AJAX match successful: {result.get('match_id')}")
                    print(f"   Journal ID: {result.get('journal_id')}")
                else:
                    print(f"❌ AJAX match failed: {result.get('error')}")
                    return False
            else:
                print(f"❌ AJAX request failed with status: {response.status_code}")
                print(f"   Response: {response.content.decode()}")
                return False
        else:
            print("⚠️  No additional unmatched transactions for AJAX test")
        
        print("\n🎉 All tests passed successfully!")
        print(f"📈 Final Statistics:")
        final_progress = ReconciliationService.get_reconciliation_progress(bank_account)
        print(f"   Matched: {final_progress.get('matched_transactions', 0)} transactions")
        print(f"   Remaining: {final_progress.get('unmatched_transactions', 0)} unmatched")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_reconciliation_workflow()
    if success:
        print("\n✅ Reconciliation system is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Reconciliation system has issues!")
        sys.exit(1)
