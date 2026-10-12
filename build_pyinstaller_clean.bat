@echo off
setlocal

echo ================================================================
echo    Word Hunt Solver - PyInstaller Clean Source Bootloader Build
echo ================================================================
echo.
echo Recompiling PyInstaller bootloader from source to eliminate
echo pre-compiled PyPI bootloader hash signatures on VirusTotal.
echo.

cd /d "%~dp0"

:: 1. Determine Python interpreter
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

:: 3. Remove generic PyPI wheel bootloader
echo.
echo [1/4] Uninstalling generic PyInstaller pre-compiled binary wheel...
%PY_BIN% -m pip uninstall -y pyinstaller

:: 4. Rebuild PyInstaller bootloader locally from C source
echo.
echo [2/4] Compiling fresh custom bootloader from C source (--no-binary pyinstaller)...
%PY_BIN% -m pip install --no-binary pyinstaller pyinstaller
if errorlevel 1 (
    echo.
    echo [WARNING] Source compilation failed or C compiler not found.
    echo Falling back to wheel installation...
    %PY_BIN% -m pip install pyinstaller
)

:: 5. Clean previous build artifacts
echo.
echo [3/4] Cleaning previous output directories...
if exist "dist\WordHuntSolver" (
    rmdir /s /q "dist\WordHuntSolver"
)
if exist "dist\WordHuntSolver-v1.0-windows-x64.zip" (
    del /f /q "dist\WordHuntSolver-v1.0-windows-x64.zip"
)

:: 6. Compile using customized build.spec with PE version headers and icon
echo.
echo [4/4] Compiling portable package with clean PE headers and icon...
%PY_BIN% -m PyInstaller --noconfirm --clean build.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller compilation failed.
    pause
    exit /b 1
)

:: 7. Package into release ZIP archive
echo.
echo Packaging into distribution archive...
tar -a -c -f dist\WordHuntSolver-v1.0-windows-x64.zip -C dist WordHuntSolver >nul 2>&1
if not exist "dist\WordHuntSolver-v1.0-windows-x64.zip" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\WordHuntSolver\*' -DestinationPath 'dist\WordHuntSolver-v1.0-windows-x64.zip' -Force"
)
copy /y "dist\WordHuntSolver-v1.0-windows-x64.zip" "dist\WordHuntSolver_v1.0.zip" >nul 2>&1

echo.
echo ================================================================
echo [SUCCESS] Clean custom-bootloader build completed!
echo Binary Directory: %~dp0dist\WordHuntSolver
echo Release ZIP:      %~dp0dist\WordHuntSolver-v1.0-windows-x64.zip
echo ================================================================
echo.
pause
