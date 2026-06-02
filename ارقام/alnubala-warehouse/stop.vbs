Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "taskkill /f /im python.exe", 0, False
