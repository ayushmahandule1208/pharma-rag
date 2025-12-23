"""
FastAPI routes for Pharma RAG API.

Enhanced with:
- Query guard results
- Detailed timing metrics
- Score breakdowns (BM25, vector, rerank)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import uuid

from app.db import DocumentStore, VectorStore
from app.services import PharmaRAG, MetricsService

router = APIRouter(prefix="/api")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    use_hybrid: bool = True
    use_reranker: bool = True
    use_guard: bool = True


class SourceResponse(BaseModel):
    drug: str
    section: str
    score: float
    is_priority: bool
    bm25_score: Optional[float] = 0.0
    vector_score: Optional[float] = 0.0
    rerank_score: Optional[float] = 0.0
    text: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class TimingResponse(BaseModel):
    retrieve_ms: Optional[int] = 0
    generate_ms: Optional[int] = 0
    total_ms: int = 0


class GuardResultResponse(BaseModel):
    passed: bool
    category: str
    confidence: float


class QueryResponse(BaseModel):
    answer: str
    query_type: str
    sources: list[SourceResponse]
    timing: Optional[TimingResponse] = None
    guard_result: Optional[GuardResultResponse] = None


class MetricsResponse(BaseModel):
    families: int
    documents: int
    search_units: int
    queries_logged: int
    vectors: int
    avg_response_time: float
    avg_score: float


class SearchStatsResponse(BaseModel):
    total_documents: int
    bm25_indexed: int
    vector_indexed: int
    reranker_enabled: bool
    embedding_model: str
    reranker_model: Optional[str] = None


# ============================================================================
# SINGLETON RAG INSTANCE (for performance)
# ============================================================================

_rag_instance = None

def get_rag_instance(use_hybrid: bool = True, use_reranker: bool = True, use_guard: bool = True) -> PharmaRAG:
    """Get or create RAG instance (cached for performance)."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = PharmaRAG(
            use_hybrid=use_hybrid,
            use_reranker=use_reranker,
            use_guard=use_guard
        )
    return _rag_instance


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system with full pipeline.
    
    Features:
    - Multi-layer query guard
    - Hybrid search (BM25 + Vector)
    - Cross-encoder re-ranking
    - Query classification
    """
    try:
        rag = get_rag_instance(
            use_hybrid=request.use_hybrid,
            use_reranker=request.use_reranker,
            use_guard=request.use_guard
        )
        
        result = rag.query(request.question, top_k=request.top_k)
        
        # Extract timing
        timing = result.get("timing", {})
        timing_response = TimingResponse(
            retrieve_ms=timing.get("retrieve_ms", 0),
            generate_ms=timing.get("generate_ms", 0),
            total_ms=timing.get("total_ms", 0)
        )
        
        # Extract guard result
        guard_result = result.get("guard_result")
        guard_response = None
        if guard_result:
            guard_response = GuardResultResponse(
                passed=guard_result.get("passed", True),
                category=guard_result.get("category", "pharmaceutical"),
                confidence=guard_result.get("confidence", 1.0)
            )
        
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
            response_time_ms=timing.get("total_ms", 0)
        )
        
        return QueryResponse(
            answer=result["answer"],
            query_type=result["query_type"],
            sources=[
                SourceResponse(
                    drug=s.get("drug", "Unknown"),
                    section=s.get("section", ""),
                    score=s.get("score", 0),
                    is_priority=s.get("is_priority", False),
                    bm25_score=s.get("bm25_score", 0),
                    vector_score=s.get("vector_score", 0),
                    rerank_score=s.get("rerank_score", 0),
                )
                for s in sources
            ],
            timing=timing_response,
            guard_result=guard_response
        )
    except Exception as e:
        import traceback
        print(f"[API Error] {traceback.format_exc()}")
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


@router.get("/search/stats", response_model=SearchStatsResponse)
async def get_search_stats():
    """Get hybrid search engine statistics."""
    try:
        from app.services.hybrid_search import get_hybrid_engine
        engine = get_hybrid_engine()
        stats = engine.get_stats()
        
        return SearchStatsResponse(
            total_documents=stats.get("total_documents", 0),
            bm25_indexed=stats.get("bm25_indexed", 0),
            vector_indexed=stats.get("vector_indexed", 0),
            reranker_enabled=stats.get("reranker_enabled", False),
            embedding_model=stats.get("embedding_model", "all-MiniLM-L6-v2"),
            reranker_model=stats.get("reranker_model"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/rebuild")
async def rebuild_search_index():
    """Rebuild the hybrid search index (call after adding new documents)."""
    try:
        from app.services.hybrid_search import get_hybrid_engine
        engine = get_hybrid_engine()
        engine.rebuild_indices()
        
        return {"status": "success", "message": "Search indices rebuilt"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "features": {
            "hybrid_search": True,
            "reranking": True,
            "query_guard": True
        }
    }
