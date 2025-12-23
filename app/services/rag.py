"""
Pharma-Intelligent RAG System (Industry-Standard Pipeline)

Key Features:
1. Query Guard - Multi-layer defense against irrelevant queries
2. Hybrid Search - BM25 + Vector with Reciprocal Rank Fusion
3. Cross-Encoder Re-ranking - Higher quality top results
4. Query Classification - Understands regulatory intent
5. Smart Retrieval - Prioritizes relevant sections
6. Compliance-Safe Responses - Citations + disclaimers
"""
import re
import time
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from openai import OpenAI

from app.db import DocumentStore


# ============================================================================
# QUERY CLASSIFICATION
# ============================================================================

class QueryType(Enum):
    SAFETY = "safety"
    EFFICACY = "efficacy"
    DOSING = "dosing"
    MECHANISM = "mechanism"
    INDICATION = "indication"
    COMPARISON = "comparison"
    SEMANTIC = "semantic"  # Generic pharma question
    CONVERSATIONAL = "conversational"  # Handled by guard
    UNKNOWN = "unknown"  # Non-pharma


# Patterns to detect query type
QUERY_PATTERNS = {
    QueryType.SAFETY: [
        r'\b(side effect|adverse|warning|contraindication|risk|toxicity|death|fatal|black.?box)\b',
        r'\bcan .* cause\b', r'\bis .* safe\b', r'\bdanger\b'
    ],
    QueryType.EFFICACY: [
        r'\b(efficacy|effective|work|benefit|outcome|clinical trial|study|results)\b',
        r'\bdoes .* work\b', r'\bhow well\b', r'\bsuccess\b'
    ],
    QueryType.DOSING: [
        r'\b(dose|dosage|dosing|mg|ml|administration|how much|how often|frequency)\b',
        r'\btake\b', r'\badminister\b', r'\bprescribe\b'
    ],
    QueryType.MECHANISM: [
        r'\b(mechanism|how does .* work|pharmacology|receptor|inhibitor|agonist|antagonist)\b',
        r'\bmoa\b', r'\btarget\b'
    ],
    QueryType.INDICATION: [
        r'\b(indication|approved for|treat|treats|used for|what .* treat|use|uses)\b',
        r'\bapproved\b', r'\bfda\b'
    ],
    QueryType.COMPARISON: [
        r'\b(compare|versus|vs|better than|difference|similar to)\b'
    ],
}

# Search strategy per query type
STRATEGIES = {
    QueryType.SAFETY: {
        "priority_sections": ["boxed warning", "warnings", "adverse", "contraindication", "precaution"],
        "boost": 1.5,
    },
    QueryType.EFFICACY: {
        "priority_sections": ["clinical studies", "efficacy", "indication", "clinical pharmacology"],
        "boost": 1.3,
    },
    QueryType.DOSING: {
        "priority_sections": ["dosage", "administration", "how supplied", "dosing"],
        "boost": 1.5,
    },
    QueryType.MECHANISM: {
        "priority_sections": ["pharmacology", "mechanism", "clinical pharmacology", "pharmacodynamics"],
        "boost": 1.2,
    },
    QueryType.INDICATION: {
        "priority_sections": ["indication", "usage", "approved"],
        "boost": 1.3,
    },
    QueryType.COMPARISON: {
        "priority_sections": ["clinical studies", "indication", "efficacy"],
        "boost": 1.2,
    },
    QueryType.SEMANTIC: {
        "priority_sections": [],
        "boost": 1.0,
    },
    QueryType.UNKNOWN: {
        "priority_sections": [],
        "boost": 1.0,
    },
}


def classify_query(query: str) -> QueryType:
    """Classify query intent based on patterns."""
    query_lower = query.lower()
    scores = {qt: 0 for qt in QueryType if qt not in [QueryType.CONVERSATIONAL, QueryType.UNKNOWN, QueryType.SEMANTIC]}
    
    for qtype, patterns in QUERY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                scores[qtype] += 1
    
    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return QueryType.SEMANTIC  # Default to general semantic search
    
    return max(scores.items(), key=lambda x: x[1])[0]


# ============================================================================
# SEARCH RESULT
# ============================================================================

@dataclass
class SearchResult:
    """Enhanced search result with regulatory context."""
    chunk_id: str
    text: str
    score: float
    section_title: str
    section_type: str
    doc_id: str
    page_start: int
    page_end: int
    is_priority: bool = False
    
    # Scores breakdown
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rerank_score: float = 0.0
    
    # Document metadata
    drug_name: str = ""
    authority: str = ""


# ============================================================================
# INTELLIGENT RETRIEVER (with Hybrid Search)
# ============================================================================

class PharmaRetriever:
    """
    Retrieves chunks with pharma-specific intelligence.
    
    Uses hybrid search (BM25 + Vector) with optional re-ranking.
    """
    
    def __init__(self, use_hybrid: bool = True, use_reranker: bool = True):
        self.use_hybrid = use_hybrid
        self.use_reranker = use_reranker
        self.sql_db = DocumentStore()
        
        # Try to use hybrid search engine
        self.hybrid_engine = None
        self.vector_store = None
        
        if use_hybrid:
            try:
                from app.services.hybrid_search import get_hybrid_engine
                self.hybrid_engine = get_hybrid_engine(use_reranker=use_reranker)
                print("[Retriever] Using hybrid search with re-ranking")
            except Exception as e:
                print(f"[Retriever] Hybrid search unavailable: {e}")
                use_hybrid = False
        
        if not use_hybrid:
            # Fallback to basic vector store
            from app.db import VectorStore
            self.vector_store = VectorStore()
            print("[Retriever] Using basic vector search")
    
    def retrieve(self, query: str, top_k: int = 5, query_type: QueryType = None) -> list[SearchResult]:
        """
        Smart retrieval with section prioritization.
        
        Args:
            query: User query
            top_k: Number of results
            query_type: Pre-classified query type (optional)
        
        Returns:
            List of SearchResult objects
        """
        # Classify if not provided
        if query_type is None:
            query_type = classify_query(query)
        
        strategy = STRATEGIES.get(query_type, STRATEGIES[QueryType.SEMANTIC])
        
        print(f"[Retriever] Query Type: {query_type.value}")
        print(f"[Retriever] Priority sections: {strategy['priority_sections']}")
        
        # Get raw results
        if self.hybrid_engine:
            raw_results = self._hybrid_retrieve(query, top_k)
        else:
            raw_results = self._basic_retrieve(query, top_k)
        
        # Enrich and boost priority sections
        enriched = self._enrich_and_boost(raw_results, strategy)
        
        # Sort by final score
        enriched.sort(key=lambda x: x.score, reverse=True)
        
        return enriched[:top_k]
    
    def _hybrid_retrieve(self, query: str, top_k: int) -> list[SearchResult]:
        """Retrieve using hybrid search engine."""
        results = self.hybrid_engine.search(
            query, 
            top_k=top_k * 2,  # Get more for post-processing
            use_rerank=self.use_reranker
        )
        
        # Convert to SearchResult objects
        return [
            SearchResult(
                chunk_id=r.unit_id,
                text=r.content,
                score=r.final_score,
                section_title=r.section_title,
                section_type=r.section_type,
                doc_id=r.doc_id,
                page_start=r.page_start,
                page_end=r.page_end,
                bm25_score=r.bm25_score,
                vector_score=r.vector_score,
                rerank_score=r.rerank_score,
                drug_name=r.drug_name,
                authority=r.authority,
            )
            for r in results
        ]
    
    def _basic_retrieve(self, query: str, top_k: int) -> list[SearchResult]:
        """Fallback to basic vector search."""
        raw_results = self.vector_store.search(query, top_k=top_k * 3)
        
        doc_cache = {}
        results = []
        
        for r in raw_results:
            doc_id = r["metadata"]["doc_id"]
            
            # Get doc info from SQL
            if doc_id not in doc_cache:
                with self.sql_db._conn() as conn:
                    row = conn.execute(
                        "SELECT drug_name, authority FROM documents WHERE doc_id=?",
                        (doc_id,)
                    ).fetchone()
                    doc_cache[doc_id] = dict(row) if row else {}
            
            doc_info = doc_cache.get(doc_id, {})
            
            results.append(SearchResult(
                chunk_id=r["id"],
                text=r["text"],
                score=r["score"],
                section_title=r["metadata"]["section_title"],
                section_type=r["metadata"]["section_type"],
                doc_id=doc_id,
                page_start=r["metadata"]["page_start"],
                page_end=r["metadata"]["page_end"],
                vector_score=r["score"],
                drug_name=doc_info.get("drug_name", "Unknown"),
                authority=doc_info.get("authority", "FDA"),
            ))
        
        return results
    
    def _enrich_and_boost(
        self, 
        results: list[SearchResult], 
        strategy: dict
    ) -> list[SearchResult]:
        """Apply section priority boosting."""
        priority_sections = strategy.get("priority_sections", [])
        boost = strategy.get("boost", 1.0)
        
        for r in results:
            section_title_lower = r.section_title.lower()
            
            # Check if priority section
            is_priority = any(
                ps in section_title_lower 
                for ps in priority_sections
            )
            
            r.is_priority = is_priority
            if is_priority:
                r.score *= boost
        
        return results


# ============================================================================
# RESPONSE GENERATOR
# ============================================================================

class ResponseGenerator:
    """Generate compliant responses with citations."""
    
    def __init__(self, api_keys: list[str] = None):
        self.api_keys = api_keys or []
        self.current_key_idx = 0
        self.client = None
        if self.api_keys:
            self.client = OpenAI(api_key=self.api_keys[0])
    
    def generate(
        self, 
        query: str, 
        results: list[SearchResult], 
        query_type: QueryType
    ) -> str:
        """Generate response with citations."""
        
        # Build context
        context = self._build_context(results)
        
        # Build prompt
        prompt = self._build_prompt(query, context, query_type)
        
        # Generate (or return context if no API key)
        if self.client:
            answer = self._call_llm(prompt)
        else:
            answer = self._fallback_response(query, results)
        
        # Add citations
        answer += self._format_citations(results)
        
        # Add disclaimer
        answer += self._get_disclaimer(query_type)
        
        return answer
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with key rotation on failure."""
        for attempt in range(len(self.api_keys)):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[warn] API key {self.current_key_idx + 1} failed: {e}")
                # Try next key
                self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                self.client = OpenAI(api_key=self.api_keys[self.current_key_idx])
                print(f"   Trying key {self.current_key_idx + 1}...")
        
        return "Error: All API keys failed. Using fallback response."
    
    def _build_context(self, results: list[SearchResult]) -> str:
        """Build context from results."""
        parts = []
        for i, r in enumerate(results, 1):
            # Add score info for transparency
            score_info = f"(relevance: {r.score:.2f}"
            if r.rerank_score > 0:
                score_info += f", rerank: {r.rerank_score:.2f}"
            score_info += ")"
            
            parts.append(f"""[Source {i}] {score_info}
Drug: {r.drug_name}
Section: {r.section_title}
Text: {r.text}
""")
        return "\n---\n".join(parts)
    
    def _build_prompt(self, query: str, context: str, query_type: QueryType) -> str:
        """Build LLM prompt."""
        instructions = {
            QueryType.SAFETY: "IMPORTANT: Mention any Boxed Warnings first. Use exact safety language from the labels.",
            QueryType.DOSING: "Provide exact dosing as stated in the label. Include administration route and frequency.",
            QueryType.EFFICACY: "Include specific endpoints and statistical results from clinical trials.",
            QueryType.MECHANISM: "Explain the mechanism of action clearly, referencing pharmacology sections.",
            QueryType.INDICATION: "List all FDA-approved indications with any limitations of use.",
        }.get(query_type, "Answer based on the regulatory information provided.")
        
        return f"""You are a pharmaceutical regulatory affairs assistant. Answer using ONLY the provided sources.

{instructions}

CONTEXT:
{context}

QUESTION: {query}

INSTRUCTIONS:
- Cite sources as [Source X]
- If information is insufficient, say so clearly
- Be precise with regulatory language
- Never make up or infer information not in the sources

ANSWER:"""
    
    def _fallback_response(self, query: str, results: list[SearchResult]) -> str:
        """Simple response when no LLM available."""
        if not results:
            return "No relevant information found in the database."
        
        # Check if we have quality results
        top_score = max(r.score for r in results) if results else 0
        if top_score < 0.3:
            return "Limited relevant information found. Please try a more specific query."
        
        answer = f"Based on FDA-approved labeling:\n\n"
        for i, r in enumerate(results[:3], 1):
            answer += f"**{r.drug_name} - {r.section_title}** [Source {i}]:\n"
            # Truncate long text
            text = r.text[:500] + "..." if len(r.text) > 500 else r.text
            answer += f"{text}\n\n"
        
        return answer
    
    def _format_citations(self, results: list[SearchResult]) -> str:
        """Format source citations."""
        if not results:
            return ""
        
        citations = "\n\n---\n**Sources:**\n"
        for i, r in enumerate(results[:5], 1):
            citations += f"{i}. {r.drug_name} - {r.section_title} "
            citations += f"({r.authority}, Pages {r.page_start}-{r.page_end})\n"
        return citations
    
    def _get_disclaimer(self, query_type: QueryType) -> str:
        """Get appropriate disclaimer."""
        disclaimers = {
            QueryType.SAFETY: "\n\n⚠️ For complete safety information, consult the full prescribing information.",
            QueryType.DOSING: "\n\n⚠️ Dosing should be determined by healthcare providers based on patient factors.",
        }
        return disclaimers.get(
            query_type,
            "\n\nℹ️ This information is from regulatory documents. Consult healthcare providers for clinical decisions."
        )


# ============================================================================
# MAIN RAG SYSTEM (with Query Guard)
# ============================================================================

class PharmaRAG:
    """
    Complete pharma-intelligent RAG system with industry-standard features:
    
    - Query Guard: Multi-layer defense against irrelevant queries
    - Hybrid Search: BM25 + Vector with RRF fusion
    - Re-ranking: Cross-encoder for better top results
    - Query Classification: Intent-based retrieval strategy
    """
    
    def __init__(
        self, 
        api_keys: list[str] = None,
        use_hybrid: bool = True,
        use_reranker: bool = True,
        use_guard: bool = True
    ):
        from app.core.config import API_KEYS
        
        self.use_guard = use_guard
        
        # Initialize query guard
        self.query_guard = None
        if use_guard:
            try:
                from app.services.query_guard import get_query_guard
                self.query_guard = get_query_guard()
                print("[RAG] Query guard enabled")
            except Exception as e:
                print(f"[RAG] Query guard unavailable: {e}")
        
        # Initialize retriever with hybrid search
        self.retriever = PharmaRetriever(
            use_hybrid=use_hybrid, 
            use_reranker=use_reranker
        )
        
        # Initialize generator
        keys = api_keys or API_KEYS
        self.generator = ResponseGenerator(api_keys=keys)
        
        print("[RAG] System initialized")
    
    def query(self, question: str, top_k: int = 5) -> dict:
        """
        Main query interface with full pipeline.
        
        Returns:
            answer: Generated response with citations
            query_type: Detected query intent
            sources: List of source metadata
            timing: Performance metrics
            guard_result: Query guard evaluation (if enabled)
        """
        start_time = time.time()
        
        # =========================================================
        # LAYER 1: Query Guard (multi-layer defense)
        # =========================================================
        guard_result = None
        if self.use_guard and self.query_guard:
            guard_result = self.query_guard.evaluate(question)
            
            if not guard_result.should_proceed:
                return {
                    "answer": guard_result.message,
                    "query_type": guard_result.category.value,
                    "sources": [],
                    "timing": {
                        "total_ms": int((time.time() - start_time) * 1000)
                    },
                    "guard_result": {
                        "passed": False,
                        "category": guard_result.category.value,
                        "confidence": guard_result.confidence
                    }
                }
        
        # =========================================================
        # LAYER 2: Query Classification
        # =========================================================
        query_type = classify_query(question)
        
        # =========================================================
        # LAYER 3: Hybrid Retrieval + Re-ranking
        # =========================================================
        retrieve_start = time.time()
        results = self.retriever.retrieve(question, top_k=top_k, query_type=query_type)
        retrieve_time = time.time() - retrieve_start
        
        # =========================================================
        # LAYER 4: Post-retrieval quality check
        # =========================================================
        if self.use_guard and self.query_guard and guard_result:
            quality_check = self.query_guard.validate_results(results, question, guard_result)
            
            if not quality_check.should_proceed:
                return {
                    "answer": quality_check.message,
                    "query_type": query_type.value,
                    "sources": [],
                    "timing": {
                        "retrieve_ms": int(retrieve_time * 1000),
                        "total_ms": int((time.time() - start_time) * 1000)
                    },
                    "guard_result": {
                        "passed": False,
                        "category": quality_check.category.value,
                        "confidence": quality_check.confidence,
                        "reason": "low_quality_results"
                    }
                }
        
        # =========================================================
        # LAYER 5: Response Generation
        # =========================================================
        generate_start = time.time()
        answer = self.generator.generate(question, results, query_type)
        generate_time = time.time() - generate_start
        
        total_time = time.time() - start_time
        
        return {
            "answer": answer,
            "query_type": query_type.value,
            "sources": [
                {
                    "drug": r.drug_name,
                    "section": r.section_title,
                    "score": round(r.score, 3),
                    "bm25_score": round(r.bm25_score, 3),
                    "vector_score": round(r.vector_score, 3),
                    "rerank_score": round(r.rerank_score, 3),
                    "is_priority": r.is_priority,
                }
                for r in results
            ],
            "timing": {
                "retrieve_ms": int(retrieve_time * 1000),
                "generate_ms": int(generate_time * 1000),
                "total_ms": int(total_time * 1000)
            },
            "guard_result": {
                "passed": True,
                "category": guard_result.category.value if guard_result else "pharmaceutical",
                "confidence": guard_result.confidence if guard_result else 1.0
            } if guard_result else None
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    """Interactive query CLI."""
    from app.core.config import API_KEYS
    
    print("\n" + "="*60)
    print("  PharmaRAG - Industry-Standard RAG Pipeline")
    print("="*60)
    
    print("\n✅ Features:")
    print("   • Multi-layer query guard")
    print("   • Hybrid search (BM25 + Vector)")
    print("   • Cross-encoder re-ranking")
    print("   • Query classification")
    
    if not API_KEYS:
        print("\n⚠️  No API keys found - using fallback responses")
    else:
        print(f"\n✅ {len(API_KEYS)} API keys loaded")
    
    rag = PharmaRAG()
    
    print("\nType your question (or 'quit' to exit):\n")
    
    while True:
        question = input("> ").strip()
        if question.lower() in ["quit", "exit", "q"]:
            break
        if not question:
            continue
        
        result = rag.query(question)
        
        print(f"\n[Type: {result['query_type']}]")
        if result.get('timing'):
            print(f"[Time: {result['timing']['total_ms']}ms]")
        if result.get('guard_result'):
            gr = result['guard_result']
            print(f"[Guard: {'✅ PASS' if gr['passed'] else '🛡️ BLOCKED'} ({gr['category']}, conf: {gr['confidence']:.2f})]")
        
        print(f"\n{result['answer']}")
        print("\n" + "-"*60 + "\n")


if __name__ == "__main__":
    main()
