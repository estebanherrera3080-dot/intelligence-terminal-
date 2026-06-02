@echo off
REM ========================================
REM Run Tests
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════╗
echo ║  🧪 RUNNING TESTS                                  ║
echo ╚════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo Running unit tests with coverage...
echo.

python -m pytest tests/ -v --cov=app --cov-report=html

echo.
echo ✅ Tests complete!
echo.
echo Coverage report generated in: htmlcov\index.html
echo.

pause
