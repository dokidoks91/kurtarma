@echo off
REM Build script for Instagram Post Planner Windows executable
REM This script builds InstagramPostPlanner.exe using PyInstaller

echo ========================================
echo Instagram Post Planner - Build Script
echo ========================================
echo.
echo Building from: %CD%
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Cleaning old build artifacts...
if exist build (
    echo Removing build\ directory...
    rmdir /s /q build
)
if exist dist (
    echo Removing dist\ directory...
    rmdir /s /q dist
)
if exist __pycache__ (
    echo Removing __pycache__\ directory...
    rmdir /s /q __pycache__
)
echo Old artifacts cleaned.
echo.

echo [2/5] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/5] Installing PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo [4/5] Verifying source code version...
python -c "import sys; sys.path.insert(0, '.'); exec(open('gui_app_v2.py', encoding='utf-8').read().split('class PlannerGUI')[0]); print('Window title check: OK' if 'Tercihli Fix v2' in open('gui_app_v2.py', encoding='utf-8').read() else 'Window title check: FAILED - OLD VERSION')"
echo.

echo [5/5] Building executable...
python -m PyInstaller InstagramPostPlanner.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [5/5] Build complete!
echo.
echo ========================================
echo SUCCESS: Executable created!
echo ========================================
echo.
echo Location: dist\InstagramPostPlanner.exe
echo.
echo You can now:
echo 1. Run dist\InstagramPostPlanner.exe directly
echo 2. Copy InstagramPostPlanner.exe to any Windows machine
echo.
echo Note: The .exe file is 80-100MB due to pandas. This is normal.
echo.
pause
