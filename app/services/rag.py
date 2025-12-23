"""
Pharma-Intelligent RAG System

Key Features:
1. Query Classification - Understands regulatory intent
2. Smart Retrieval - Prioritizes relevant sections
3. Compliance-Safe Responses - Citations + disclaimers
"""
import re
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from openai import OpenAI

from app.db import DocumentStore
from app.db.vector_store import VectorStore


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


# Patterns to detect query type
QUERY_PATTERNS = {
    QueryType.SAFETY: [
        r'\b(side effect|adverse|warning|contraindication|risk|toxicity|death|fatal)\b',
        r'\bcan .* cause\b', r'\bis .* safe\b'
    ],
    QueryType.EFFICACY: [
        r'\b(efficacy|effective|work|benefit|outcome|clinical trial|study)\b',
        r'\bdoes .* work\b', r'\bhow well\b'
    ],
    QueryType.DOSING: [
        r'\b(dose|dosage|dosing|mg|administration|how much|how often)\b'
    ],
    QueryType.MECHANISM: [
        r'\b(mechanism|how does .* work|pharmacology|receptor|inhibitor)\b'
    ],
    QueryType.INDICATION: [
        r'\b(indication|approved for|treat|used for|what .* treat)\b'
    ],
    QueryType.COMPARISON: [
        r'\b(compare|versus|vs|better than|difference)\b'
    ],
}

# Search strategy per query type
STRATEGIES = {
    QueryType.SAFETY: {
        "priority_sections": ["boxed warning", "warnings", "adverse", "contraindication"],
        "boost": 1.5,
    },
    QueryType.EFFICACY: {
        "priority_sections": ["clinical studies", "efficacy", "indication"],
        "boost": 1.3,
    },
    QueryType.DOSING: {
        "priority_sections": ["dosage", "administration"],
        "boost": 1.5,
    },
    QueryType.MECHANISM: {
        "priority_sections": ["pharmacology", "mechanism", "clinical pharmacology"],
        "boost": 1.2,
    },
    QueryType.INDICATION: {
        "priority_sections": ["indication", "usage"],
        "boost": 1.3,
    },
    QueryType.COMPARISON: {
        "priority_sections": ["clinical studies", "indication"],
        "boost": 1.2,
    },
}


def classify_query(query: str) -> QueryType:
    """Classify query intent based on patterns."""
    query_lower = query.lower()
    scores = {qt: 0 for qt in QueryType}
    
    for qtype, patterns in QUERY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                scores[qtype] += 1
    
    max_score = max(scores.values())
    if max_score == 0:
        return QueryType.INDICATION
    
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
    
    # Added from SQL join
    drug_name: str = ""
    authority: str = ""


# ============================================================================
# INTELLIGENT RETRIEVER
# ============================================================================

class PharmaRetriever:
    """Retrieves chunks with pharma-specific intelligence."""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.sql_db = DocumentStore()
    
    def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Smart retrieval with section prioritization."""
        # 1. Classify query
        query_type = classify_query(query)
        strategy = STRATEGIES[query_type]
        
        print(f"[Query Type] {query_type.value}")
        print(f"[Priority] {strategy['priority_sections']}")
        
        # 2. Vector search (get more candidates)
        raw_results = self.vector_store.search(query, top_k=top_k * 3)
        
        # 3. Enrich with SQL data
        doc_cache = {}
        enriched = []
        
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
            section_title = r["metadata"]["section_title"].lower()
            
            # Check if priority section
            is_priority = any(
                ps in section_title 
                for ps in strategy["priority_sections"]
            )
            
            # Calculate boosted score
            score = r["score"]
            if is_priority:
                score *= strategy["boost"]
            
            enriched.append(SearchResult(
                chunk_id=r["id"],
                text=r["text"],
                score=score,
                section_title=r["metadata"]["section_title"],
                section_type=r["metadata"]["section_type"],
                doc_id=doc_id,
                page_start=r["metadata"]["page_start"],
                page_end=r["metadata"]["page_end"],
                is_priority=is_priority,
                drug_name=doc_info.get("drug_name", "Unknown"),
                authority=doc_info.get("authority", "FDA"),
            ))
        
        # 4. Sort by boosted score
        enriched.sort(key=lambda x: x.score, reverse=True)
        
        return enriched[:top_k]


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
            parts.append(f"""[Source {i}]
Drug: {r.drug_name}
Section: {r.section_title}
Text: {r.text}
""")
        return "\n---\n".join(parts)
    
    def _build_prompt(self, query: str, context: str, query_type: QueryType) -> str:
        """Build LLM prompt."""
        instructions = {
            QueryType.SAFETY: "IMPORTANT: Mention any Boxed Warnings first. Use exact safety language.",
            QueryType.DOSING: "Provide exact dosing as stated in the label.",
            QueryType.EFFICACY: "Include specific endpoints and statistical results.",
        }.get(query_type, "")
        
        return f"""You are a regulatory affairs assistant. Answer using ONLY the provided sources.

{instructions}

CONTEXT:
{context}

QUESTION: {query}

INSTRUCTIONS:
- Cite sources as [Source X]
- If information is insufficient, say so
- Be precise with regulatory language

ANSWER:"""
    
    def _fallback_response(self, query: str, results: list[SearchResult]) -> str:
        """Simple response when no LLM available."""
        if not results:
            return "No relevant information found."
        
        answer = f"Based on FDA-approved labeling:\n\n"
        for i, r in enumerate(results[:3], 1):
            answer += f"**{r.drug_name} - {r.section_title}** [Source {i}]:\n"
            answer += f"{r.text[:500]}...\n\n"
        
        return answer
    
    def _format_citations(self, results: list[SearchResult]) -> str:
        """Format source citations."""
        citations = "\n\n---\n**Sources:**\n"
        for i, r in enumerate(results, 1):
            citations += f"{i}. {r.drug_name} - {r.section_title} "
            citations += f"({r.authority}, Pages {r.page_start}-{r.page_end})\n"
        return citations
    
    def _get_disclaimer(self, query_type: QueryType) -> str:
        """Get appropriate disclaimer."""
        disclaimers = {
            QueryType.SAFETY: "\n\n[!] For complete safety information, consult the full prescribing information.",
            QueryType.DOSING: "\n\n[!] Dosing should be determined by healthcare providers based on patient factors.",
        }
        return disclaimers.get(
            query_type,
            "\n\n[i] This information is from regulatory documents. Consult healthcare providers for clinical decisions."
        )


# ============================================================================
# MAIN RAG SYSTEM
# ============================================================================

class PharmaRAG:
    """Complete pharma-intelligent RAG system."""
    
    def __init__(self, api_keys: list[str] = None):
        from app.core.config import API_KEYS
        self.retriever = PharmaRetriever()
        keys = api_keys or API_KEYS
        self.generator = ResponseGenerator(api_keys=keys)
    
    def query(self, question: str, top_k: int = 5) -> dict:
        """
        Main query interface.
        
        Returns:
            answer: Generated response with citations
            query_type: Detected query intent
            sources: List of source metadata
        """
        # Classify
        query_type = classify_query(question)
        
        # Retrieve
        results = self.retriever.retrieve(question, top_k=top_k)
        
        # Generate
        answer = self.generator.generate(question, results, query_type)
        
        return {
            "answer": answer,
            "query_type": query_type.value,
            "sources": [
                {
                    "drug": r.drug_name,
                    "section": r.section_title,
                    "score": round(r.score, 3),
                    "is_priority": r.is_priority,
                }
                for r in results
            ]
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    """Interactive query CLI."""
    from app.core.config import API_KEYS
    
    print("\n" + "="*50)
    print("Pharma RAG System")
    print("="*50)
    
    if not API_KEYS:
        print("[warn] No API keys found - using fallback responses")
    else:
        print(f"[ok] {len(API_KEYS)} API keys loaded")
    
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
        print(f"\n{result['answer']}")
        print("\n" + "-"*50 + "\n")


if __name__ == "__main__":
    main()
