"""
PharmaRAG - Industry-Standard RAG Pipeline

Features:
- Multi-layer Query Guard (conversational filtering, relevance checking)
- Hybrid Search (BM25 + Vector with Reciprocal Rank Fusion)
- Cross-Encoder Re-ranking for better top results
- Query Classification with intent-based retrieval

Run the API server:
    uvicorn main:application --reload

For Hugging Face Spaces:
    uvicorn main:application --host 0.0.0.0 --port 7860
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core import settings


application = FastAPI(
    title="PharmaRAG API",
    description="""
## Pharmaceutical Regulatory Intelligence System

Industry-standard RAG pipeline for FDA drug label information.

### Features:
- **Multi-layer Query Guard**: Handles conversational queries, gibberish, and non-pharma questions gracefully
- **Hybrid Search**: BM25 (keyword) + Vector (semantic) search with Reciprocal Rank Fusion
- **Cross-Encoder Re-ranking**: Higher quality top results
- **Query Classification**: Intent-based retrieval strategies (safety, dosing, efficacy, etc.)

### Example Queries:
- "What are the side effects of Ozempic?"
- "What is Keytruda approved for?"
- "How is Humira dosed?"
""",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for HuggingFace Spaces
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
application.include_router(router)


def initialize_data():
    """Auto-initialize: download sample data, ingest, and index vectors."""
    from app.db import DocumentStore, VectorStore
    from app.services import IngestionService
    
    db = DocumentStore()
    stats = db.get_stats()
    
    # Step 1: Ingest documents if none exist
    if stats["documents"] == 0:
        print("\n[Auto-Init] No documents found. Running ingestion...")
        ingestion = IngestionService()
        ingestion.run(download=True, force=False)
        stats = db.get_stats()
        print(f"[Auto-Init] Ingested {stats['documents']} documents, {stats['search_units']} chunks")
    else:
        print(f"\n[Auto-Init] Found {stats['documents']} documents, {stats['search_units']} chunks")
    
    # Step 2: Index vectors if needed
    vs = VectorStore()
    vector_stats = vs.get_stats()
    
    if vector_stats["total_vectors"] < stats["search_units"]:
        print(f"[Auto-Init] Indexing vectors ({vector_stats['total_vectors']} -> {stats['search_units']})...")
        vs.index_all()
        vector_stats = vs.get_stats()
    
    print(f"[Auto-Init] Vector store ready: {vector_stats['total_vectors']} vectors")
    print("[Auto-Init] Done!\n")


@application.on_event("startup")
async def startup_event():
    """Initialize data on startup."""
    print("\n" + "="*60)
    print("  PharmaRAG - Industry-Standard RAG Pipeline v2.0")
    print("="*60)
    print("\n✅ Features enabled:")
    print("   • Multi-layer Query Guard")
    print("   • Hybrid Search (BM25 + Vector)")
    print("   • Cross-Encoder Re-ranking")
    print("   • Query Classification")
    
    # Skip init on HuggingFace if data already exists or in read-only mode
    if os.getenv("SKIP_INIT") != "true":
        try:
            initialize_data()
        except Exception as e:
            print(f"[Warning] Auto-init failed: {e}")
    
    print("\n" + "="*60 + "\n")


@application.get("/")
async def root():
    return {
        "name": "PharmaRAG API",
        "version": "2.0.0",
        "description": "Industry-standard pharmaceutical RAG pipeline",
        "features": [
            "Multi-layer Query Guard",
            "Hybrid Search (BM25 + Vector)",
            "Cross-Encoder Re-ranking",
            "Query Classification"
        ],
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
        "main:application",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


def print_help():
    print("""
PharmaRAG - Industry-Standard Regulatory Intelligence System v2.0

Features:
  ✓ Multi-layer Query Guard (handles "How are you?" gracefully)
  ✓ Hybrid Search (BM25 + Vector with RRF)
  ✓ Cross-Encoder Re-ranking
  ✓ Query Classification

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
