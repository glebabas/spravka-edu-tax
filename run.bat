@echo off
title SpravkaEduTax

echo =====================================================================
echo  SpravkaEduTax - Zapusk prilozheniya
echo =====================================================================
echo.

set PY_EXE=

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto found_python
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=py"
    goto found_python
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto found_python
)

echo [ERROR] Python not found on your PC!
echo Please install Python 3.10+ from python.org
pause
exit /b 1

:found_python
echo [1/2] Proverka bibliotek pypdf, reportlab, openpyxl...
"%PY_EXE%" -m pip install -r requirements.txt --quiet

echo [2/2] Zapusk servera prilozheniya...
echo.
"%PY_EXE%" app.py

pause
