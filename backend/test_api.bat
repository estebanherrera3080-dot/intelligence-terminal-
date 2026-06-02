@echo off
REM ========================================
REM Quick API Test
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║  🧪 QUICK API TEST                                 ║
echo ║     Make sure server is running on :8000           ║
echo ╚════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

timeout /t 2 >nul

echo 1️⃣  Testing API Health...
curl.exe "http://localhost:8000/health" 2>nul | find "healthy" >nul
if %errorlevel% equ 0 (
    echo ✅ API is running!
) else (
    echo ❌ API not responding. Make sure server is running.
    echo Run: python -m uvicorn app.main:app --reload --port 8000
    pause
    exit /b 1
)

echo.
echo 2️⃣  Fetching XAUUSD symbols...
curl.exe "http://localhost:8000/api/v1/market/symbols" 2>nul
echo.

echo.
echo 3️⃣  Fetching XAUUSD latest price...
curl.exe "http://localhost:8000/api/v1/market/latest?symbol=XAUUSD" 2>nul
echo.

echo.
echo 4️⃣  Fetching XAUUSD OHLCV (5 candles)...
curl.exe "http://localhost:8000/api/v1/market/ohlcv?symbol=XAUUSD&timeframe=1h&limit=5" 2>nul
echo.

echo.
echo ✅ API test complete!
echo.
echo To see full API documentation, open in browser:
echo http://localhost:8000/docs
echo.

pause
