@echo off
REM ========================================
REM INTELLIGENCE TERMINAL - Setup Script (Windows)
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║  🏛️  INTELLIGENCE TERMINAL - SETUP               ║
echo ║     Institutional Gold Trading Terminal             ║
echo ╚════════════════════════════════════════════════════╝
echo.

REM Check Python version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Navigate to backend directory
cd /d "%~dp0"
echo.
echo Current directory: %cd%

REM Step 1: Upgrade pip
echo.
echo 📦 Upgrading pip...
python -m pip install --upgrade pip

REM Step 2: Install requirements
echo.
echo 📥 Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ✅ Dependencies installed successfully!

REM Step 3: Test imports
echo.
echo 🧪 Testing imports...
python -c "import fastapi; print('✅ FastAPI OK')"
python -c "import pydantic; print('✅ Pydantic OK')"
python -c "import httpx; print('✅ httpx OK')"
python -c "import sqlalchemy; print('✅ SQLAlchemy OK')"

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║  ✅ SETUP COMPLETE                                 ║
echo ╚════════════════════════════════════════════════════╝
echo.
echo Next steps:
echo.
echo 1️⃣  Start the API server (this window will stay open):
echo    python -m uvicorn app.main:app --reload --port 8000
echo.
echo 2️⃣  In a NEW terminal, test the API:
echo    python test_api.py
echo.
echo 3️⃣  Or open in browser:
echo    http://localhost:8000/docs
echo.
echo 4️⃣  To run tests:
echo    pytest tests/ -v
echo.
pause
