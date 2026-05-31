$taskName = "WMS Warehouse Server"
$vbsPath = "C:\web-projects\start.vbs"
$action = New-ScheduledTaskAction -Execute "cscript.exe" -Argument "//nologo `"$vbsPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "INTERACTIVE" -LogonType InteractiveToken -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force
Write-Host "تم تثبيت الخدمة — السيرفر هيشتغل تلقائياً عند تسجيل الدخول"
