@echo off
setlocal

echo ================================================================
echo       Word Hunt Solver - Modern Nuitka C++ Native Compiler
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Determine Python interpreter (prefer dedicated build_venv if available)
set "PY_BIN=python"
if exist "build_venv\Scripts\python.exe" (
    set "PY_BIN=build_venv\Scripts\python.exe"
    echo [*] Using build virtual environment: build_venv
) else (
    echo [*] Using system Python from PATH
)

:: 2. Ensure assets and icons exist
if not exist "assets\words.txt" (
    if exist "dictionary.txt" (
        copy /y "dictionary.txt" "assets\words.txt" >nul
    )
)

:: 3. Install Nuitka and acceleration dependencies
echo [1/3] Checking and installing Nuitka compiler requirements...
%PY_BIN% -m pip install nuitka zstandard ordered-set

:: 4. Clean previous Nuitka dist
if exist "dist_nuitka" (
    echo [2/3] Cleaning previous Nuitka build artifacts...
    rmdir /s /q "dist_nuitka"
)

:: 5. Compile directly to native C++ binary
echo [3/3] Compiling native Windows binary with Nuitka (PyQt6 plugin enabled)...
%PY_BIN% -m nuitka ^
    --standalone ^
    --windows-disable-console ^
    --enable-plugin=pyqt6 ^
    --include-data-dir=assets=assets ^
    --include-data-files=dictionary.txt=dictionary.txt ^
    --windows-icon-from-ico=assets\icon.ico ^
    --windows-company-name="OpenSource Community" ^
    --windows-product-name="Word Hunt Solver" ^
    --windows-file-version=1.0.0.0 ^
    --windows-product-version=1.0.0.0 ^
    --windows-file-description="Word Hunt & Connect Solver Utility" ^
    --output-dir=dist_nuitka ^
    --main=main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Nuitka compilation failed. Please ensure a C compiler (MSVC or MinGW64) is installed.
    pause
    exit /b 1
)

:: 6. Package Nuitka distribution archive
echo.
echo Packaging Nuitka native build into ZIP archive...
tar -a -c -f dist_nuitka\WordHuntSolver-v1.0-nuitka-windows-x64.zip -C dist_nuitka main.dist >nul 2>&1
if not exist "dist_nuitka\WordHuntSolver-v1.0-nuitka-windows-x64.zip" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist_nuitka\main.dist\*' -DestinationPath 'dist_nuitka\WordHuntSolver-v1.0-nuitka-windows-x64.zip' -Force"
)

echo.
echo ================================================================
echo [SUCCESS] Nuitka native compilation complete!
echo Native binary directory: %~dp0dist_nuitka\main.dist
echo Release ZIP archive:     %~dp0dist_nuitka\WordHuntSolver-v1.0-nuitka-windows-x64.zip
echo.
echo Nuitka translates Python to C++, linking directly with the
echo Python C-API without PyInstaller runtime stubs or heuristics.
echo ================================================================
echo.
pause
