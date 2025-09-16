#!/usr/bin/env python3
"""
WORKSPACE CLEANUP SCRIPT
========================

This script identifies and removes unnecessary files from the Django workspace
while preserving essential application code and configuration files.
"""

import os
import shutil
from pathlib import Path

def get_files_to_cleanup():
    """
    Identify all files that can be safely removed.
    Returns a dictionary categorized by file type.
    """
    base_path = Path("d:/Again")
    
    cleanup_files = {
        'documentation': [],
        'test_scripts': [],
        'analysis_scripts': [],
        'debug_scripts': [],
        'sample_data': [],
        'temp_files': [],
        'log_files': []
    }
    
    # Documentation files (.md)
    md_files = [
        "ADMIN_INTERFACE_LOGIC_EXPLANATION.md",
        "XERO_STYLE_JOURNAL_BEHAVIOR.md", 
        "XERO_STYLE_DASHBOARD_SUCCESS_REPORT.md",
        "VISUAL_JOURNAL_WALKTHROUGH.md",
        "SPLIT_TRANSACTION_IMPLEMENTATION_SUCCESS.md",
        "SPLIT_TRANSACTION_ERROR_ANALYSIS.md",
        "RESTART_RECONCILIATION_IMPLEMENTATION_REPORT.md",
        "RECONCILIATION_SUCCESS_REPORT.md",
        "MULTI_COMPANY_AUDIT_REPORT.md",
        "MISSING_REPORTS_IMPLEMENTATION_SUCCESS.md",
        "MANUAL_JOURNAL_ENTRIES_EXPLANATION_PRINTABLE.md",
        "MANUAL_JOURNAL_CREATION_GUIDE.md",
        "LOAN_MODULE_IMPLEMENTATION_GUIDE.md",
        "IMPLEMENTATION_SUCCESS_REPORT.md",
        "FIXED_ASSET_IMPLEMENTATION_SUCCESS_REPORT.md",
        "FIXED_ASSET_IMPLEMENTATION_PLAN.md",
        "FIXED_ASSET_DATABASE_IMPLEMENTATION_PLAN.md",
        "FINAL_SUCCESS_REPORT.md",
        "EDIT_RECONCILIATION_SUCCESS_REPORT.md",
        "DJANGO_SERVER_ERROR_FIXED_SUCCESS.md",
        "DASHBOARD_MISSING_VALUES_FIXED.md",
        "DATA_POPULATION_SUCCESS_REPORT.md",
        "CONVERSION_BALANCES_GUIDE.md",
        "COMPREHENSIVE_SYSTEM_TESTING_GUIDE.md"
    ]
    
    # Text documentation files (.txt)
    txt_files = [
        "WHO_FIELD_QUICK_REFERENCE.txt",
        "transaction_who_recommendations.txt",
        "SPLIT_TRANSACTIONS_DETAILED_GUIDE.txt",
        "OPERATING_TRANSACTIONS_WHO_GUIDE.txt",
        "COMPLETE_WHO_WHAT_SPLITS_GUIDE.txt",
        "COMPLETE_PAYROLL_GOLOMT_GUIDE.txt",
        "COMPLETE_43_TRANSACTIONS_WHO_GUIDE.txt"
    ]
    
    # Test scripts
    test_files = [
        "test_split_implementation.py",
        "test_reports.py", 
        "test_reconciliation_workflow.py",
        "test_multi_company_isolation.py",
        "test_gold_coa.py",
        "test_form_rendering.py",
        "test_form_debug.py",
        "test_enhanced_coa.py",
        "test_edit_form.py",
        "test_depreciation_rendering.py",
        "test_depreciation_basis_form.py",
        "test_decimal_calc.py",
        "test_dashboard_values.py",
        "test_dashboard_quick.py",
        "test_dashboard.py",
        "test_dashboard_direct.py",
        "test_asset_detail.py",
        "test_assets_list_data.py"
    ]
    
    # Analysis scripts
    analysis_files = [
        "analyze_system_architecture.py",
        "analyze_split_transactions.py",
        "analyze_golomt_payroll_data.py", 
        "analyze_accounting_system.py"
    ]
    
    # Debug scripts
    debug_files = [
        "debug_dashboard_context.py",
        "debug_asset_list.py"
    ]
    
    # Check scripts
    check_files = [
        "check_transaction.py",
        "check_status.py",
        "check_golomt_transactions.py",
        "check_excel_data.py",
        "check_depreciation_method.py",
        "check_data.py",
        "check_companies.py",
        "check_balances.py",
        "check_asset_order.py",
        "check_assets.py"
    ]
    
    # Sample/test data files
    sample_data_files = [
        "test_new_date_format.csv",
        "test_csv_format.csv",
        "sample_transactions_smart_test.csv",
        "sample_bank_statement.csv",
        "realistic_payroll_transactions_2025.csv",
        "realistic_operating_transactions_2025.csv",
        "tax_rates_2025_semicolon.csv",
        "tax_rates_2025.tsv"
    ]
    
    # Utility/cleanup scripts  
    utility_files = [
        "cleanup_failed_uploads.py",
        "cleanup_orphaned_transactions.py",
        "cleanup_trial_balance.py",
        "clear_transactions.py",
        "create_actual_golomt_guide.py",
        "create_demo_data.py",
        "create_journal_demo.py",
        "create_sample_asset_types.py",
        "create_test_journal.py",
        "create_test_user.py",
        "complete_who_what_splits_guide.py",
        "explain_bank_transaction_balancing.py",
        "explain_split_functionality.py",
        "fix_preferences.py",
        "fix_transactions.py",
        "lookup_account_codes.py",
        "operating_account_who_guidance.py",
        "populate_company_fields.py",
        "populate_data_from_excel.py",
        "post_delete_check.py",
        "recalculate_balances.py",
        "reconciliation_analysis.py",
        "reconciliation_structure_recommended.py",
        "setup_accounting_system.py",
        "show_users.py",
        "system_audit.py",
        "update_conversion_current.py",
        "upload_csv_data.py",
        "verify_accounting_setup.py",
        "verify_conversion_current.py",
        "verify_imported_data.py"
    ]
    
    # Log files
    log_files = [
        "debug_admin.log"
    ]
    
    # Categorize files
    cleanup_files['documentation'].extend(md_files)
    cleanup_files['documentation'].extend(txt_files)
    cleanup_files['test_scripts'].extend(test_files)
    cleanup_files['analysis_scripts'].extend(analysis_files)
    cleanup_files['analysis_scripts'].extend(check_files)
    cleanup_files['debug_scripts'].extend(debug_files)
    cleanup_files['sample_data'].extend(sample_data_files)
    cleanup_files['temp_files'].extend(utility_files)
    cleanup_files['log_files'].extend(log_files)
    
    return cleanup_files

def get_files_to_preserve():
    """
    List of essential files that should NOT be deleted.
    """
    essential_files = [
        "README.md",  # Keep main README
        "requirements.txt",  # Keep Python dependencies
        "manage.py",  # Django management
        "db.sqlite3",  # Database file
        ".env",  # Environment variables
        ".gitignore",  # Git configuration
        
        # Essential data files (production data)
        "chart_of_accounts_q1_2025.csv",
        "manual_journal_entries_q1_2025.csv", 
        "fixed_assets_q1_2025.csv",
        "bank_transactions_operating_q1_2025.csv",
        "bank_transactions_operating_q1_2025_fixed.csv",
        "bank_transactions_payroll_q1_2025.csv",
        "bank_transactions_payroll_q1_2025_clean.csv",
        "bank_transactions_payroll_q1_2025_fixed.csv",
        "tax_rates_2025.csv"
    ]
    
    # Essential directories (Django apps)
    essential_dirs = [
        "django_env",  # Virtual environment
        "static",      # Static files
        "media",       # Media files
        "templates",   # Template files
        "myproject",   # Django project settings
        "core",        # Core app
        "company",     # Company management
        "coa",         # Chart of accounts
        "bank_accounts", # Bank management
        "journal",     # Journal entries
        "reconciliation", # Reconciliation
        "assets",      # Fixed assets
        "reports",     # Reporting
        "users",       # User management
        "conversion",  # Data conversion
        "setup",       # Setup utilities
        "api",         # API endpoints
        "files"        # File storage
    ]
    
    return essential_files, essential_dirs

def preview_cleanup():
    """
    Show what files will be deleted without actually deleting them.
    """
    print("🧹 WORKSPACE CLEANUP PREVIEW")
    print("=" * 60)
    
    cleanup_files = get_files_to_cleanup()
    essential_files, essential_dirs = get_files_to_preserve()
    
    total_files = 0
    total_size = 0
    
    for category, files in cleanup_files.items():
        if files:
            print(f"\n📁 {category.upper().replace('_', ' ')}")
            print("-" * 40)
            
            category_size = 0
            for file in files:
                file_path = Path("d:/Again") / file
                if file_path.exists():
                    size = file_path.stat().st_size
                    category_size += size
                    print(f"   🗑️ {file:<50} ({size:,} bytes)")
                    total_files += 1
                else:
                    print(f"   ❓ {file:<50} (not found)")
            
            total_size += category_size
            print(f"   📊 Category total: {len([f for f in files if (Path('d:/Again') / f).exists()])} files, {category_size:,} bytes")
    
    print(f"\n📊 CLEANUP SUMMARY")
    print("-" * 40)
    print(f"   🗑️ Total files to delete: {total_files}")
    print(f"   💾 Total size to free: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    
    print(f"\n✅ ESSENTIAL FILES TO PRESERVE")
    print("-" * 40)
    for file in essential_files:
        file_path = Path("d:/Again") / file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"   🔒 {file:<50} ({size:,} bytes)")
    
    print(f"\n✅ ESSENTIAL DIRECTORIES TO PRESERVE")
    print("-" * 40)
    for dir_name in essential_dirs:
        dir_path = Path("d:/Again") / dir_name
        if dir_path.exists():
            print(f"   📁 {dir_name}/")

def perform_cleanup(confirm=False):
    """
    Actually delete the unnecessary files.
    """
    if not confirm:
        print("⚠️ Add confirm=True to actually delete files")
        return
    
    print("🧹 PERFORMING WORKSPACE CLEANUP")
    print("=" * 60)
    
    cleanup_files = get_files_to_cleanup()
    deleted_files = 0
    freed_space = 0
    
    for category, files in cleanup_files.items():
        print(f"\n🗑️ Cleaning {category.replace('_', ' ')}...")
        
        for file in files:
            file_path = Path("d:/Again") / file
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    print(f"   ✅ Deleted: {file}")
                    deleted_files += 1
                    freed_space += size
                except Exception as e:
                    print(f"   ❌ Error deleting {file}: {e}")
            else:
                print(f"   ⏭️ Skipped: {file} (not found)")
    
    print(f"\n🎉 CLEANUP COMPLETED")
    print("-" * 40)
    print(f"   ✅ Deleted files: {deleted_files}")
    print(f"   💾 Freed space: {freed_space:,} bytes ({freed_space/1024/1024:.2f} MB)")

if __name__ == "__main__":
    # First show preview
    preview_cleanup()
    
    print(f"\n⚠️ WARNING")
    print("-" * 40)
    print("This will permanently delete the files listed above.")
    print("Make sure you have backups if needed.")
    print("To proceed with cleanup, run:")
    print("   perform_cleanup(confirm=True)")
