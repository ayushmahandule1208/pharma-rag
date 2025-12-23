"""
Pharma RAG - Main Entry Point

Run the API server:
    uvicorn main:app --reload

Or run CLI ingestion:
    python main.py ingest <pdf_file>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from app.api import router
from app.core import settings


app = FastAPI(
    title=settings.API_TITLE,
    description="Pharmaceutical Regulatory Intelligence System - RAG Pipeline",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "Pharma RAG API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "running",
    }


def cli_ingest(pdf_filename: str):
    """Run ingestion from command line."""
    from datetime import date
    from app.services import IngestionService
    from app.models import RegulatoryFiling
    from app.core import file_hash
    
    pdf_path = settings.RAW_DIR / pdf_filename
    
    if not pdf_path.exists():
        print(f"[Error] PDF not found: {pdf_path}")
        print(f"   Place your PDF in: {settings.RAW_DIR}")
        sys.exit(1)
    
    filing = RegulatoryFiling(
        filing_id=f"NDA_{pdf_path.stem}",
        authority="FDA",
        document_type="NDA",
        document_family=f"NDA_{pdf_path.stem}",
        drug_name="Unknown",
        generic_name="Unknown",
        therapeutic_area="Unknown",
        approval_pathway="Unknown",
        file_hash=file_hash(pdf_path),
    )
    
    service = IngestionService()
    result = service.ingest(pdf_path, filing)
    
    print(f"\n[Result] {result.final_search_units} search units created")


def cli_serve():
    """Start the API server."""
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


def print_help():
    print("""
Pharma RAG - Regulatory Intelligence System

Usage:
    python main.py <command> [args]

Commands:
    serve              Start the API server
    ingest <pdf>       Ingest a PDF from data/raw/

Examples:
    python main.py serve
    python main.py ingest 213260s000lbl.pdf

API Docs:
    http://localhost:8000/docs
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "serve":
        cli_serve()
    elif command == "ingest":
        if len(sys.argv) < 3:
            print("[Error] Usage: python main.py ingest <pdf_filename>")
            sys.exit(1)
        cli_ingest(sys.argv[2])
    elif command in ["--help", "-h", "help"]:
        print_help()
    else:
        print(f"[Error] Unknown command: {command}")
        print_help()
        sys.exit(1)
