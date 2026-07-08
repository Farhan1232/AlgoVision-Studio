@echo off
REM ============================================================
REM  Build AlgoVision Studio into a single Windows .exe
REM  Run this on Windows (double-click or from a terminal).
REM  Requires Python 3.11+ on PATH.
REM ============================================================

echo [1/4] Creating virtual environment...
python -m venv .venv
if errorlevel 1 goto :error

echo [2/4] Installing dependencies + PyInstaller...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo [3/4] Building executable with PyInstaller...
pyinstaller --noconfirm algovision.spec
if errorlevel 1 goto :error

echo [4/4] Done!
echo.
echo   The executable is at:  dist\AlgoVisionStudio.exe
echo.
pause
exit /b 0

:error
echo.
echo Build failed. See the messages above.
pause
exit /b 1
