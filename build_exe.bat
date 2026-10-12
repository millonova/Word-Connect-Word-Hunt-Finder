@echo off
setlocal

echo ================================================================
echo       Word Hunt Solver - Windows Standalone Build Pipeline
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.10+ and add it to your PATH.
    echo.
    pause
    exit /b 1
)

:: 2. Provision dedicated build virtual environment
if not exist "build_venv\Scripts\python.exe" (
    echo [1/5] Creating dedicated build virtual environment build_venv...
    python -m venv build_venv
    if errorlevel 1 (
        echo [ERROR] Failed to create build_venv.
        pause
        exit /b 1
    )
) else (
    echo [1/5] Using existing build virtual environment build_venv...
)

:: 3. Upgrade pip and install build dependencies
echo [2/5] Installing pinned dependencies and PyInstaller...
build_venv\Scripts\python.exe -m pip install --upgrade pip
build_venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

:: 4. Verify templates and assets
echo [3/5] Verifying assets and templates...
if not exist "assets\words.txt" (
    if exist "dictionary.txt" (
        copy /y "dictionary.txt" "assets\words.txt" >nul
    )
)

build_venv\Scripts\python.exe -c "import sys; from core.template_matcher import TemplateMatcher; from core.dictionary import WordDictionary; tm = TemplateMatcher(); wd = WordDictionary(); print('  [OK] Templates loaded:', len(tm.templates), 'glyphs'); print('  [OK] Dictionary loaded:', len(wd.words), 'words')"
if errorlevel 1 (
    echo [ERROR] Asset verification failed.
    pause
    exit /b 1
)

:: 5. Compile executable with PyInstaller
echo [4/5] Compiling clean standalone Windows portable folder with PyInstaller...
if exist "dist\WordHuntSolver" (
    echo   Cleaning previous build output...
    rmdir /s /q "dist\WordHuntSolver"
)
if exist "dist\WordHuntSolver-v1.0-windows-x64.zip" (
    del /f /q "dist\WordHuntSolver-v1.0-windows-x64.zip"
)
if exist "dist\WordHuntSolver_v1.0.zip" (
    del /f /q "dist\WordHuntSolver_v1.0.zip"
)

build_venv\Scripts\python.exe -m PyInstaller --noconfirm --clean build.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller compilation failed.
    pause
    exit /b 1
)

:: 6. Package into clean release ZIP archive (portable onedir)
tar -a -c -f dist\WordHuntSolver-v1.0-windows-x64.zip -C dist WordHuntSolver >nul 2>&1
if not exist "dist\WordHuntSolver-v1.0-windows-x64.zip" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\WordHuntSolver\*' -DestinationPath 'dist\WordHuntSolver-v1.0-windows-x64.zip' -Force"
)
:: Also copy to legacy name for backward compatibility
copy /y "dist\WordHuntSolver-v1.0-windows-x64.zip" "dist\WordHuntSolver_v1.0.zip" >nul 2>&1

if exist "dist\WordHuntSolver-v1.0-windows-x64.zip" (
    echo.
    echo ================================================================
    echo [SUCCESS] Clean portable package built successfully.
    echo Distribution directory: %~dp0dist\WordHuntSolver
    echo Release ZIP archive:    %~dp0dist\WordHuntSolver-v1.0-windows-x64.zip
    echo.
    echo Open disk inspection: All DLLs and byte-code are visible in folder.
    echo Zero temp-folder runtime unpacking (eliminates injector heuristics).
    echo Users can unzip WordHuntSolver-v1.0-windows-x64.zip and
    echo run WordHuntSolver.exe directly.
    echo ================================================================
) else (
    echo [WARNING] Binary created in dist\WordHuntSolver, but ZIP creation had an issue.
)

echo.
pause
