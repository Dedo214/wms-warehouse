@echo off
chcp 65001 >nul
title نظام إدارة المخازن WMS v2.0
echo =====================================================
echo   بدء تشغيل نظام إدارة المخازن WMS v2.0
echo =====================================================
echo.
echo جاري تشغيل الخادم...
echo.
set PYTHONPATH=C:\web-projects
"C:\Users\Celia&Mesk\AppData\Local\Programs\Python\Python311\python.exe" "C:\web-projects\run.py"
pause