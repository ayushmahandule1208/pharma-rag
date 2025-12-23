"""
Run the FastAPI server.

Usage:
    python run_server.py
    python run_server.py --skip-init   # Skip auto-initialization
    
Then access:
    - API: http://localhost:8000/api
    - Docs: http://localhost:8000/docs
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router


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


app = FastAPI(
    title="PharmaRAG API",
    description="Pharma-intelligent RAG system for regulatory documents",
    version="1.0.0",
)

# CORS for frontend (supports local dev and production)
import os
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "PharmaRAG API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    print("\n" + "="*50)
    print("Starting PharmaRAG API Server")
    print("="*50)
    
    # Auto-initialize data unless --skip-init is passed
    if "--skip-init" not in sys.argv:
        initialize_data()
    
    print("API:  http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
