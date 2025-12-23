"""Pydantic schemas (for API phase)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SearchUnit(BaseModel):
    """Indexed chunk for RAG."""
    unit_id: str
    doc_id: str
    section_number: str
    section_title: str
    section_type: str
    content: str
    fingerprint: str
    chunk_index: int = 0
    page_start: int
    page_end: int


class QueryRequest(BaseModel):
    """User query."""
    question: str
    filters: Optional[dict] = None
    top_k: int = 5


class QueryResponse(BaseModel):
    """RAG response."""
    answer: str
    sources: list[dict] = Field(default_factory=list)
