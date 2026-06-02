Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\web-projects"
WshShell.Run """C:\Users\Celia&Mesk\AppData\Local\Programs\Python\Python311\python.exe"" run.py", 0, False
