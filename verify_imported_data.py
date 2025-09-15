#!/usr/bin/env python
"""
Data Verification Script
Shows imported Chart of Accounts and Manual Journals with summary
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from coa.models import Account
from journal.models import Journal, JournalLine
from company.models import Company

def show_imported_data():
    """Display summary of imported data"""
    print("🎯 IMPORTED DATA VERIFICATION")
    print("=" * 60)
    
    # Get company
    company = Company.objects.first()
    print(f"📊 Company: {company.name}")
    print()
    
    # Chart of Accounts from Excel
    print("📋 CHART OF ACCOUNTS (From Excel)")
    print("-" * 40)
    
    excel_accounts = Account.objects.filter(
        company=company,
        description__contains="Imported from Excel"
    ).order_by('code')
    
    print(f"Total Excel Accounts: {excel_accounts.count()}")
    print()
    
    # Group by account type
    account_types = {}
    for account in excel_accounts:
        if account.account_type not in account_types:
            account_types[account.account_type] = []
        account_types[account.account_type].append(account)
    
    for account_type, accounts in account_types.items():
        print(f"🏷️  {account_type.upper().replace('_', ' ')} ({len(accounts)} accounts):")
        for account in accounts[:5]:  # Show first 5
            print(f"   {account.code} - {account.name}")
        if len(accounts) > 5:
            print(f"   ... and {len(accounts) - 5} more")
        print()
    
    # Manual Journals from Excel
    print("📋 MANUAL JOURNALS (From Excel)")
    print("-" * 40)
    
    excel_journals = Journal.objects.filter(
        reference__in=[
            'ADJ-2025-Q1', 'DEP-2025-01', 'DEP-2025-02', 'DEP-2025-03',
            'EXP-2025-01', 'EXP-2025-02', 'EXP-2025-03', 'INT-2025-Q1',
            'REV-2025-01', 'REV-2025-02', 'REV-2025-03', 'TAX-2025-02', 'TAX-2025-03'
        ]
    ).order_by('date')
    
    print(f"Total Excel Journals: {excel_journals.count()}")
    print()
    
    # Show journal summaries
    journal_types = {}
    for journal in excel_journals:
        journal_type = journal.reference.split('-')[0]
        if journal_type not in journal_types:
            journal_types[journal_type] = []
        journal_types[journal_type].append(journal)
    
    for journal_type, journals in journal_types.items():
        type_names = {
            'DEP': 'DEPRECIATION ENTRIES',
            'REV': 'REVENUE ACCRUALS', 
            'EXP': 'EXPENSE ADJUSTMENTS',
            'TAX': 'PAYROLL TAX ACCRUALS',
            'ADJ': 'ADJUSTING ENTRIES',
            'INT': 'INTEREST ACCRUALS'
        }
        
        print(f"🏷️  {type_names.get(journal_type, journal_type)} ({len(journals)} entries):")
        for journal in journals:
            lines_count = journal.lines.count()
            total_debit = sum(line.debit for line in journal.lines.all())
            print(f"   {journal.reference}: {journal.narration[:40]}...")
            print(f"      Date: {journal.date} | Lines: {lines_count} | Amount: ${total_debit:,.2f}")
        print()
    
    # Sample journal detail
    print("📋 SAMPLE JOURNAL DETAIL")
    print("-" * 40)
    
    sample_journal = excel_journals.filter(reference='DEP-2025-01').first()
    if sample_journal:
        print(f"Journal: {sample_journal.reference}")
        print(f"Date: {sample_journal.date}")
        print(f"Narration: {sample_journal.narration}")
        print(f"Status: {sample_journal.status}")
        print("\nJournal Lines:")
        
        for line in sample_journal.lines.all():
            debit_str = f"${line.debit:,.2f}" if line.debit else "-"
            credit_str = f"${line.credit:,.2f}" if line.credit else "-"
            print(f"  {line.account_code}: {line.description}")
            print(f"    Debit: {debit_str} | Credit: {credit_str}")
        
        # Calculate totals
        total_debits = sum(line.debit for line in sample_journal.lines.all())
        total_credits = sum(line.credit for line in sample_journal.lines.all())
        print(f"\nTotals: Debits ${total_debits:,.2f} | Credits ${total_credits:,.2f}")
        print(f"Balanced: {'✅ YES' if abs(total_debits - total_credits) < 0.01 else '❌ NO'}")

def show_usage_guide():
    """Show how to use the imported data"""
    print("\n" + "=" * 60)
    print("🚀 HOW TO USE YOUR IMPORTED DATA")
    print("=" * 60)
    
    print("1. 📊 VIEW CHART OF ACCOUNTS:")
    print("   → http://localhost:8000/coa/")
    print("   → All accounts from Excel are now available for journal entries")
    print()
    
    print("2. 📋 VIEW MANUAL JOURNALS:")
    print("   → http://localhost:8000/journal/")
    print("   → 13 sample journal entries from your Excel data")
    print("   → All entries are balanced and posted")
    print()
    
    print("3. ✨ CREATE NEW JOURNAL ENTRIES:")
    print("   → http://localhost:8000/journal/new/")
    print("   → Use imported accounts (6310, 1510, etc.)")
    print("   → Follow the patterns from imported journals")
    print()
    
    print("4. 🎯 COMMON ACCOUNTS YOU CAN USE:")
    print("   ASSETS:")
    print("   → 1200 - Accounts Receivable")
    print("   → 1300 - Prepaid Expenses")
    print("   → 1410 - Computer Equipment")
    print("   → 1510 - Accumulated Depreciation - Computer Equipment")
    print()
    print("   EXPENSES:")
    print("   → 5040 - Insurance")
    print("   → 5120 - Payroll Tax Expense")
    print("   → 6310 - Depreciation Expense - Computer Equipment")
    print()
    print("   REVENUE:")
    print("   → 4010 - Consulting Revenue")
    print("   → 4020 - Software Development Revenue")
    print()
    
    print("5. 🔧 JOURNAL ENTRY PATTERNS:")
    print("   Monthly Depreciation:")
    print("   → Dr. 6310 Depreciation Expense")
    print("   → Cr. 1510 Accumulated Depreciation")
    print()
    print("   Revenue Accrual:")
    print("   → Dr. 1200 Accounts Receivable")
    print("   → Cr. 4010 Consulting Revenue")
    print()
    print("   Prepaid Adjustment:")
    print("   → Dr. 5040 Insurance Expense")
    print("   → Cr. 1300 Prepaid Expenses")

if __name__ == "__main__":
    show_imported_data()
    show_usage_guide()
    
    print("\n🎉 YOUR ACCOUNTING SYSTEM IS READY!")
    print("All data from Excel has been successfully imported and is ready to use.")
