# Cleanup Script for Unnecessary Files
# This script will remove test, debug, fix files and documentation MD files

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  File Cleanup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define file patterns to remove
$testFiles = @(
    "test_*.py",
    "*_test.py",
    "quick_test.py",
    "final_test.py"
)

$debugFiles = @(
    "debug_*.py",
    "debug_*.log",
    "*_debug.py"
)

$fixFiles = @(
    "fix_*.py",
    "*_fix.py"
)

$checkFiles = @(
    "check_*.py",
    "*_check.py"
)

$analyzeFiles = @(
    "analyze_*.py",
    "*_analyze.py"
)

$demoFiles = @(
    "demo_*.py",
    "create_demo_*.py",
    "*_demo.py",
    "demo_*.xlsx"
)

$clearFiles = @(
    "clear_*.py",
    "*_clear.py"
)

$verifyFiles = @(
    "verify_*.py",
    "*_verify.py"
)

$resetFiles = @(
    "reset_*.py",
    "*_reset.py"
)

# MD documentation files (excluding important ones)
$mdFiles = @(
    "AI_FIX_TEST_INSTRUCTIONS.md",
    "AI_TEST_CHECKLIST.md",
    "AI_TRAINING_GUIDE.md",
    "BANK_RULES_ACCESS.md",
    "BANK_RULES_AUTO_POPULATE.md",
    "BANK_RULES_DEBIT_CREDIT_GUIDE.md",
    "BANK_RULES_DEBUG_NOT_MATCHING.md",
    "BANK_RULES_FIX.md",
    "BANK_RULES_GUIDE.md",
    "BANK_RULES_IMPROVEMENTS.md",
    "BANK_RULES_MATCHING_ISSUE.md",
    "BANK_RULES_SUCCESS_CONFIRMATION.md",
    "BANK_RULES_TEMPLATE_FIX.md",
    "BANK_RULES_TEST_FIX.md",
    "CLEANUP_SUMMARY.md",
    "COMPLETE_FIX_GUIDE.md",
    "DELETE_ACCOUNTS_COMPLETE_GUIDE.md",
    "DELETE_BUTTONS_TROUBLESHOOTING.md",
    "DELETION_IMPLEMENTATION_SUMMARY.md",
    "DEPLOYMENT_TESTING_GUIDE.md",
    "FINAL_STATUS_REPORT.md",
    "HOW_TO_DELETE_ACCOUNTS.md",
    "INTEGRATION_GUIDE.md",
    "MANUAL_TESTING_GUIDE.md",
    "NEW_PROGRESS_SYSTEM.md",
    "OPTIMIZATION_SUMMARY.md",
    "PERFORMANCE_OPTIMIZATIONS.md",
    "PHASE1_COMPLETE_SUMMARY.md",
    "PROGRESS_BAR_FIX.md",
    "QUICK_REFERENCE.md",
    "RESTART_SERVER_NOW.md",
    "SMART_CREDITOR_AI_PRODUCT_STRATEGY.md",
    "SMART_LEARNING_INTEGRATION_COMPLETE.md",
    "SMART_LEARNING_INTEGRATION_PHASE1_COMPLETE.md",
    "SMART_RECONCILIATION_SYSTEM_ROADMAP.md",
    "STEP_BY_STEP_MONGOLIAN.md",
    "UNDERSTANDING_MISSING_ERRORS.md",
    "WHERE_ARE_AI_SUGGESTIONS.md",
    "WORKFLOW_DIAGRAM.md"
)

# Combine all patterns
$allPatterns = $testFiles + $debugFiles + $fixFiles + $checkFiles + $analyzeFiles + $demoFiles + $clearFiles + $verifyFiles + $resetFiles

# Function to safely delete files
function Remove-Files {
    param (
        [string[]]$patterns,
        [string]$category
    )
    
    Write-Host "Removing $category..." -ForegroundColor Yellow
    $count = 0
    
    foreach ($pattern in $patterns) {
        $files = Get-ChildItem -Path "d:\Again" -Filter $pattern -File -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            try {
                Remove-Item -Path $file.FullName -Force
                Write-Host "  ✓ Removed: $($file.Name)" -ForegroundColor Green
                $count++
            } catch {
                Write-Host "  ✗ Failed to remove: $($file.Name)" -ForegroundColor Red
            }
        }
    }
    
    if ($count -eq 0) {
        Write-Host "  No files found." -ForegroundColor Gray
    } else {
        Write-Host "  Total removed: $count files" -ForegroundColor Cyan
    }
    Write-Host ""
}

# Function to delete MD files
function Remove-MDFiles {
    Write-Host "Removing documentation MD files..." -ForegroundColor Yellow
    $count = 0
    
    foreach ($mdFile in $mdFiles) {
        $filePath = "d:\Again\$mdFile"
        if (Test-Path $filePath) {
            try {
                Remove-Item -Path $filePath -Force
                Write-Host "  ✓ Removed: $mdFile" -ForegroundColor Green
                $count++
            } catch {
                Write-Host "  ✗ Failed to remove: $mdFile" -ForegroundColor Red
            }
        }
    }
    
    if ($count -eq 0) {
        Write-Host "  No files found." -ForegroundColor Gray
    } else {
        Write-Host "  Total removed: $count files" -ForegroundColor Cyan
    }
    Write-Host ""
}

# Confirm before deletion
Write-Host "This script will remove the following types of files:" -ForegroundColor Yellow
Write-Host "  - Test files (test_*.py, *_test.py)" -ForegroundColor White
Write-Host "  - Debug files (debug_*.py, debug_*.log)" -ForegroundColor White
Write-Host "  - Fix files (fix_*.py, *_fix.py)" -ForegroundColor White
Write-Host "  - Check files (check_*.py)" -ForegroundColor White
Write-Host "  - Analyze files (analyze_*.py)" -ForegroundColor White
Write-Host "  - Demo files (demo_*.py, demo_*.xlsx)" -ForegroundColor White
Write-Host "  - Clear files (clear_*.py)" -ForegroundColor White
Write-Host "  - Verify files (verify_*.py)" -ForegroundColor White
Write-Host "  - Reset files (reset_*.py)" -ForegroundColor White
Write-Host "  - Documentation MD files (various guides)" -ForegroundColor White
Write-Host ""

$confirmation = Read-Host "Do you want to proceed? (yes/no)"

if ($confirmation -ne "yes") {
    Write-Host "Cleanup cancelled." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "Starting cleanup..." -ForegroundColor Green
Write-Host ""

# Remove files by category
Remove-Files -patterns $testFiles -category "Test Files"
Remove-Files -patterns $debugFiles -category "Debug Files"
Remove-Files -patterns $fixFiles -category "Fix Files"
Remove-Files -patterns $checkFiles -category "Check Files"
Remove-Files -patterns $analyzeFiles -category "Analyze Files"
Remove-Files -patterns $demoFiles -category "Demo Files"
Remove-Files -patterns $clearFiles -category "Clear Files"
Remove-Files -patterns $verifyFiles -category "Verify Files"
Remove-Files -patterns $resetFiles -category "Reset Files"
Remove-MDFiles

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cleanup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: README.md and manage.py were preserved as they are essential files." -ForegroundColor Yellow
