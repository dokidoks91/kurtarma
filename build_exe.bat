@echo off
REM Build script for Instagram Post Planner Windows executable
REM This script builds InstagramPostPlanner.exe using PyInstaller

echo ========================================
echo Instagram Post Planner - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Installing PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo [3/4] Building executable...
python -m PyInstaller InstagramPostPlanner.spec --clean
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Build complete!
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
