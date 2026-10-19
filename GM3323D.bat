@echo off
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%my_devices.py" set "APP_DIR=%~dp0GM3323D-BatteryViewer\"
if not exist "%APP_DIR%my_devices.py" goto missing
where pyw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pyw.exe -3 "%APP_DIR%my_devices.py"
    exit /b
)
where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%APP_DIR%my_devices.py"
    exit /b
)
echo Python 3.10+ is required. Install Python with tkinter, then try again.
pause
exit /b 1
:missing
echo Extract the entire project before launching.
pause
exit /b 1
