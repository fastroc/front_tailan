# 🔄 Quick Django Server Restart Script
# Run this script to restart Django and verify AI is working

Write-Host ""
Write-Host "🔄 DJANGO SERVER RESTART & AI VERIFICATION" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Step 1: Check for running Python processes
Write-Host "Step 1: Checking for running Django server..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "  ⚠️  Found $($pythonProcesses.Count) Python process(es) running" -ForegroundColor Yellow
    Write-Host "  Please manually stop Django server:" -ForegroundColor White
    Write-Host "  1. Go to terminal running Django" -ForegroundColor White
    Write-Host "  2. Press Ctrl + C" -ForegroundColor White
    Write-Host ""
    Write-Host "  Then run this script again!" -ForegroundColor Green
    Write-Host ""
    exit
} else {
    Write-Host "  ✅ No Django server running" -ForegroundColor Green
}

Write-Host ""

# Step 2: Verify code changes exist
Write-Host "Step 2: Verifying AI fix in code..." -ForegroundColor Yellow
$ajaxViewsPath = "D:\Again\reconciliation\ajax_views.py"
$codeContent = Get-Content $ajaxViewsPath -Raw

if ($codeContent -match "TransactionMatchHistory\.objects\.create") {
    Write-Host "  ✅ AI training code found in ajax_views.py" -ForegroundColor Green
} else {
    Write-Host "  ❌ AI training code NOT found!" -ForegroundColor Red
    Write-Host "  The fix may not have been applied correctly" -ForegroundColor Red
    exit
}

if ($codeContent -match "discover_new_patterns") {
    Write-Host "  ✅ Pattern discovery code found" -ForegroundColor Green
} else {
    Write-Host "  ❌ Pattern discovery code NOT found!" -ForegroundColor Red
    exit
}

Write-Host ""

# Step 3: Start Django server
Write-Host "Step 3: Starting Django server..." -ForegroundColor Yellow
Write-Host "  Command: python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl + C to stop server when done testing" -ForegroundColor Cyan
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 2

# Change to project directory and start server
Set-Location D:\Again
& D:\Again\django_env\Scripts\python.exe manage.py runserver

Write-Host ""
Write-Host "Server stopped." -ForegroundColor Yellow
Write-Host ""
Write-Host "📊 To verify AI is working, run:" -ForegroundColor Cyan
Write-Host "  D:/Again/django_env/Scripts/python.exe D:/Again/test_ai_now.py" -ForegroundColor White
Write-Host ""
