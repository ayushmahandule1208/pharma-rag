"""
Run the complete PharmaRAG system (backend + frontend).

Usage:
    python run.py              # Start both backend and frontend
    python run.py --backend    # Start only backend
    python run.py --frontend   # Start only frontend
    python run.py --setup      # Install frontend dependencies
"""
import sys
import subprocess
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def run_backend():
    """Run FastAPI backend."""
    print("[Backend] Starting on http://localhost:8000")
    subprocess.run(
        [sys.executable, "run_server.py"],
        cwd=PROJECT_ROOT
    )


def run_frontend():
    """Run Next.js frontend."""
    print("[Frontend] Starting on http://localhost:3000")
    subprocess.run(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=True
    )


def setup_frontend():
    """Install frontend dependencies."""
    print("[Setup] Installing frontend dependencies...")
    subprocess.run(
        ["npm", "install"],
        cwd=FRONTEND_DIR,
        shell=True
    )
    print("[Setup] Done!")


def main():
    args = sys.argv[1:]
    
    if "--setup" in args:
        setup_frontend()
        return
    
    if "--backend" in args:
        run_backend()
        return
    
    if "--frontend" in args:
        run_frontend()
        return
    
    # Default: run both
    print("=" * 50)
    print("PharmaRAG - Starting Full Stack")
    print("=" * 50)
    print("\nBackend:  http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 50)
    
    # Start backend in thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait a moment for backend to start
    time.sleep(2)
    
    # Run frontend in main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()



