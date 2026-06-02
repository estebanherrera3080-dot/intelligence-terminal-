@echo off
REM ========================================
REM Start Intelligence Terminal API Server
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║  🚀 INTELLIGENCE TERMINAL API SERVER                      ║
echo ║     Starting on http://localhost:8000              ║
echo ╚════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo Starting API server with auto-reload...
echo.
echo 📡 Server will be available at:
echo    - API: http://localhost:8000
echo    - Swagger UI: http://localhost:8000/docs
echo    - ReDoc: http://localhost:8000/redoc
echo.
echo Press CTRL+C to stop the server
echo.

python -m uvicorn app.main:app --reload --port 8000

pause
