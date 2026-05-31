Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  بدء تشغيل نظام إدارة المخازن WMS v2.0" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

$pythonPath = "C:\Users\Celia&Mesk\AppData\Local\Programs\Python\Python311\python.exe"
$runScript = "C:\web-projects\run.py"

if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ لم يتم العثور على Python!" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "✅ بدء تشغيل الخادم..." -ForegroundColor Green
$env:PYTHONPATH = "C:\web-projects"
& $pythonPath $runScript

pause