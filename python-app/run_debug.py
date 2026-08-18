"""
Direct entrypoint for running FastAPI in debugger mode.

Usage:
    python run_debug.py
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.PROJECT_NAME} in DEBUG mode on http://127.0.0.1:8000 ...")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="debug",
        access_log=True,
    )
