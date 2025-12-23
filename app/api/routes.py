"""
FastAPI routes for Pharma RAG API.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import uuid

from app.db import DocumentStore, VectorStore
from app.services import PharmaRAG, MetricsService, DrugComparator

router = APIRouter(prefix="/api")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class SourceResponse(BaseModel):
    drug: str
    section: str
    score: float
    is_priority: bool
    text: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    query_type: str
    sources: list[SourceResponse]


class MetricsResponse(BaseModel):
    families: int
    documents: int
    search_units: int
    queries_logged: int
    vectors: int
    avg_response_time: float
    avg_score: float


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query the RAG system."""
    try:
        rag = PharmaRAG()
        
        start = time.time()
        result = rag.query(request.question, top_k=request.top_k)
        elapsed_ms = int((time.time() - start) * 1000)
        
        # Log query
        db = DocumentStore()
        sources = result.get("sources", [])
        top_score = sources[0]["score"] if sources else 0
        avg_score = sum(s["score"] for s in sources) / len(sources) if sources else 0
        
        db.log_query(
            query_id=str(uuid.uuid4()),
            query_text=request.question,
            query_type=result["query_type"],
            num_results=len(sources),
            top_score=top_score,
            avg_score=avg_score,
            response_time_ms=elapsed_ms
        )
        
        return QueryResponse(
            answer=result["answer"],
            query_type=result["query_type"],
            sources=[
                SourceResponse(
                    drug=s["drug"],
                    section=s["section"],
                    score=s["score"],
                    is_priority=s["is_priority"],
                )
                for s in sources
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents():
    """Get all document families."""
    try:
        db = DocumentStore()
        families = db.get_families()
        return families
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{family_id}/versions")
async def get_versions(family_id: str):
    """Get all versions of a document family."""
    try:
        db = DocumentStore()
        versions = db.get_versions(family_id)
        return versions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get system metrics."""
    try:
        db = DocumentStore()
        vs = VectorStore()
        
        sql_stats = db.get_stats()
        vector_stats = vs.get_stats()
        
        # Query stats
        query_logs = db.get_query_logs(limit=1000)
        
        if query_logs:
            avg_time = sum(q["response_time_ms"] for q in query_logs) / len(query_logs)
            avg_score = sum(q["top_score"] for q in query_logs) / len(query_logs)
        else:
            avg_time = avg_score = 0
        
        return MetricsResponse(
            families=sql_stats.get("families", 0),
            documents=sql_stats.get("documents", 0),
            search_units=sql_stats.get("search_units", 0),
            queries_logged=sql_stats.get("queries_logged", 0),
            vectors=vector_stats.get("total_vectors", 0),
            avg_response_time=round(avg_time, 2),
            avg_score=round(avg_score, 3),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# ============================================================================
# DRUG COMPARISON ROUTES
# ============================================================================

class CompareRequest(BaseModel):
    drug1: str
    drug2: str


@router.get("/drugs")
async def get_available_drugs():
    """Get list of drugs available for comparison."""
    try:
        comparator = DrugComparator()
        drugs = comparator.get_available_drugs()
        return {"drugs": drugs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_drugs(request: CompareRequest):
    """Compare two drugs side-by-side."""
    try:
        comparator = DrugComparator()
        result = comparator.compare(request.drug1, request.drug2)
        return comparator.to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
