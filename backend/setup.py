#!/usr/bin/env python
"""
Setup script for Intelligence Terminal
Installs dependencies and validates environment
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str = "") -> bool:
    """Run shell command and report status"""
    print(f"\n{'=' * 60}")
    print(f"🔧 {description}")
    print(f"{'=' * 60}")
    print(f"Command: {cmd}\n")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False)
        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            return True
        else:
            print(f"❌ FAILED: {description}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Setup Intelligence Terminal"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                                                                ║")
    print("║  🏛️  INTELLIGENCE TERMINAL - SETUP                           ║")
    print("║     Institutional Gold Trading Terminal                        ║")
    print("║                                                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    backend_dir = Path(__file__).parent
    
    # Step 1: Check Python version
    print(f"\n📌 Python Version: {sys.version}")
    if sys.version_info < (3, 11):
        print("❌ ERROR: Python 3.11+ required")
        sys.exit(1)
    
    # Step 2: Install requirements
    success = run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python dependencies"
    )
    
    if not success:
        print("\n❌ Failed to install dependencies")
        sys.exit(1)
    
    # Step 3: Validate imports
    print(f"\n{'=' * 60}")
    print("✓ Validating imports")
    print(f"{'=' * 60}\n")
    
    try:
        import fastapi
        print("✅ FastAPI imported successfully")
        
        import pydantic
        print("✅ Pydantic imported successfully")
        
        import httpx
        print("✅ httpx imported successfully")
        
        import sqlalchemy
        print("✅ SQLAlchemy imported successfully")
        
        print("\n✅ All imports successful!")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        sys.exit(1)
    
    # Step 4: Summary
    print(f"\n{'=' * 60}")
    print("✅ SETUP COMPLETE")
    print(f"{'=' * 60}")
    print("""
Next steps:

1. Start API server:
   python -m uvicorn app.main:app --reload --port 8000

2. In another terminal, test the API:
   python test_api.py

3. Or open in browser:
   http://localhost:8000/docs

4. Run tests:
   pytest tests/ -v

Happy trading! 🚀
    """)


if __name__ == "__main__":
    main()
