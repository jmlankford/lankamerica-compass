@echo off
echo ============================================
echo  LankAmerica Compass -- Build Script
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ and try again.
    pause
    exit /b 1
)

:: Check PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Convert icon if needed
if not exist "assets\icon.ico" (
    echo Generating icon...
    python -c "from PIL import Image; img=Image.open('assets/logo_small.png').convert('RGBA'); img.save('assets/icon.ico',format='ICO',sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
)

:: Clean previous build
echo Cleaning previous build...
if exist "dist\LankAmericaCompass.exe" del /f /q "dist\LankAmericaCompass.exe"
if exist "build" rmdir /s /q "build"

:: Build
echo.
echo Building executable -- this takes 1-3 minutes...
echo.
python -m PyInstaller ^
  --name "LankAmericaCompass" ^
  --onefile ^
  --windowed ^
  --icon "assets\icon.ico" ^
  --add-data "assets;assets" ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "matplotlib.backends.backend_qt5agg" ^
  --hidden-import "matplotlib.backends.backend_agg" ^
  --hidden-import "bcrypt" ^
  --collect-all "matplotlib" ^
  --collect-all "PyQt6" ^
  main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. Check output above for details.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete!
echo  Output: dist\LankAmericaCompass.exe
echo ============================================
echo.

:: Show file size
python -c "import os; s=os.path.getsize('dist/LankAmericaCompass.exe'); print(f'  File size: {s/1024/1024:.1f} MB')"
echo.

set /p OPEN="Open dist folder now? (y/n): "
if /i "%OPEN%"=="y" explorer dist

pause
