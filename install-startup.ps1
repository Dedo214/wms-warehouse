$startup = [Environment]::GetFolderPath("Startup")
$shortcut = Join-Path $startup "WMS-Server.lnk"
$wshell = New-Object -ComObject WScript.Shell
$link = $wshell.CreateShortcut($shortcut)
$link.TargetPath = "C:\Windows\System32\cscript.exe"
$link.Arguments = "//nologo `"C:\web-projects\start.vbs`""
$link.WorkingDirectory = "C:\web-projects"
$link.Description = "WMS Warehouse Server"
$link.WindowStyle = 7
$link.Save()
Write-Host "OK - Server will auto-start on login"
Write-Host ""
Write-Host "Commands:"
Write-Host "  start.vbs   -> Start server (hidden)"
Write-Host "  stop.vbs    -> Stop server"
Write-Host "  http://localhost:5000  -> Open system"
