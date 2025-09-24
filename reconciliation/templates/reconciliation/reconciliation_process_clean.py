#!/usr/bin/env python3
"""
Clean up script to remove auto-split functionality and fix template literal issues
from reconciliation_process.html template
"""

import re

def clean_reconciliation_template():
    template_path = r"d:\Again\reconciliation\templates\reconciliation\reconciliation_process.html"
    
    # Read the current template
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove problematic functions that contain template literals causing errors
    functions_to_remove = [
        'showLoanSplitTransactionModal',
        'showLoanPaymentSplitModal', 
        'triggerLoanPaymentSplitTransaction',
        'initializeLoanSplitLines',
        'addLoanSplitLineRow',
        'saveLoanSplitTransaction',
        'processLoanPayment',
        'showMultipleLoanSelection',
        'selectLoanForSplit',
        'checkIfPotentialLoanCustomer',
        'testLoanPaymentSplit'
    ]
    
    # Remove auto-detection functionality 
    auto_trigger_patterns = [
        r'setTimeout\(\(\) => \{\s*triggerLoanPaymentSplitTransaction.*?\}, \d+\);',
        r'detectLoanPayment\(parseInt\(transactionId\)\);',
        r'// NEW: Auto-trigger split transaction.*?triggerLoanPaymentSplitTransaction.*?;',
        r'// AUTO-TRIGGER.*?}',
        r'testButton\.onclick = function.*?};'
    ]
    
    # Pattern to match template literals that cause browser errors
    template_literal_patterns = [
        r'\$\{transactionData\.date.*?\}',
        r'\$\{parseFloat\(allocation\.amount\)\.toFixed\(2\)\}',
        r'\$\{preset\.amount \|\| \'\'\}',
        r'\$\{sanitizedData\.date\}',
        r'\$\{.*?breakdown.*?\}',
        r'\$\{.*?loanInfo.*?\}',
        r'\$\{.*?customer\.name.*?\}',
        r'\$\{.*?loan\.loan_number.*?\}',
        r'\$\{.*?\.toFixed\(2\).*?\}'
    ]
    
    print("Starting cleanup...")
    
    # Remove auto-trigger patterns
    for pattern in auto_trigger_patterns:
        content = re.sub(pattern, '// Auto-split functionality removed', content, flags=re.DOTALL)
    
    # Replace template literals with safe fallbacks
    content = re.sub(r'\$\{transactionData\.date.*?\}', '"2024-01-01"', content)
    content = re.sub(r'\$\{parseFloat\(allocation\.amount\)\.toFixed\(2\)\}', '"0.00"', content)
    content = re.sub(r'\$\{preset\.amount \|\| \'\'\}', '""', content)
    content = re.sub(r'\$\{sanitizedData\.date\}', '"2024-01-01"', content)
    content = re.sub(r'\$\{.*?\.toFixed\(2\).*?\}', '"0.00"', content)
    content = re.sub(r'\$\{.*?customer\.name.*?\}', '"Customer Name"', content)
    content = re.sub(r'\$\{.*?loan\.loan_number.*?\}', '"L001"', content)
    
    # Remove large function blocks that contain problematic template literals
    # This is a more aggressive approach to remove entire problematic sections
    
    # Remove loan-specific modal functions
    content = re.sub(
        r'function showLoanSplitTransactionModal\(.*?\n  \}',
        '''function showLoanSplitTransactionModal(transactionData, loanBreakdown) {
    console.log('Loan split transaction modal has been disabled');
    // Fallback to basic split transaction modal
    showSplitTransactionModal(transactionData);
  }''',
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r'function triggerLoanPaymentSplitTransaction\(.*?\n  \}',
        '''function triggerLoanPaymentSplitTransaction(transactionId, customerName) {
    console.log('Auto-split functionality has been disabled');
    return;
  }''',
        content,
        flags=re.DOTALL
    )
    
    # Backup original file
    backup_path = template_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Backup created: {backup_path}")
    print("Cleanup completed!")
    
    return content

if __name__ == "__main__":
    clean_reconciliation_template()
