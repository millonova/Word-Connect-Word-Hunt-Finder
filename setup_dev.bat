@echo off
setlocal

echo ================================================================
echo       Word Hunt Solver - Local Development Setup
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.10+ and add it to your PATH.
    echo.
    pause
    exit /b 1
)

:: 2. Create virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [1/4] Creating local virtual environment venv...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Existing virtual environment found.
)

:: 3. Install requirements
echo [2/4] Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

:: 4. Verify templates and assets
echo [3/4] Checking assets and templates...
if not exist "assets\words.txt" (
    if exist "dictionary.txt" (
        copy /y "dictionary.txt" "assets\words.txt" >nul
    )
)

venv\Scripts\python.exe -c "import sys; from core.template_matcher import TemplateMatcher; from core.dictionary import WordDictionary; tm = TemplateMatcher(); wd = WordDictionary(); print('  [OK] Templates verified:', len(tm.templates), '/ 26 characters'); print('  [OK] Word dictionary verified:', len(wd.words), 'words')"
if errorlevel 1 (
    echo [ERROR] Asset verification failed.
    pause
    exit /b 1
)

:: 5. Launch application
echo [4/4] Launching Word Hunt Desktop App...
echo.
venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error code.
    pause
)
