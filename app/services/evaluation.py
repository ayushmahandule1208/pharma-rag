"""
RAG Evaluation & Metrics

Provides:
1. System metrics (ingestion, indexing stats)
2. Retrieval quality metrics
3. Query performance tracking
4. Simple RAG evaluation
"""
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from app.db import DocumentStore, VectorStore


@dataclass
class RetrievalMetrics:
    """Metrics for a single retrieval."""
    query: str
    query_type: str
    num_results: int
    top_score: float
    avg_score: float
    min_score: float
    priority_hit_rate: float
    response_time_ms: int


@dataclass 
class SystemMetrics:
    """Overall system metrics."""
    total_families: int
    total_documents: int
    total_chunks: int
    total_vectors: int
    total_queries: int
    avg_response_time_ms: float
    avg_top_score: float
    avg_results_per_query: float


class MetricsService:
    """Track and report system metrics."""
    
    def __init__(self):
        self.sql_db = DocumentStore()
        self.vector_store = VectorStore()
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get overall system metrics."""
        sql_stats = self.sql_db.get_stats()
        vector_stats = self.vector_store.get_stats()
        
        query_logs = self.sql_db.get_query_logs(limit=1000)
        
        if query_logs:
            avg_time = sum(q["response_time_ms"] for q in query_logs) / len(query_logs)
            avg_score = sum(q["top_score"] for q in query_logs) / len(query_logs)
            avg_results = sum(q["num_results"] for q in query_logs) / len(query_logs)
        else:
            avg_time = avg_score = avg_results = 0
        
        return SystemMetrics(
            total_families=sql_stats.get("families", 0),
            total_documents=sql_stats.get("documents", 0),
            total_chunks=sql_stats.get("search_units", 0),
            total_vectors=vector_stats.get("total_vectors", 0),
            total_queries=sql_stats.get("queries_logged", 0),
            avg_response_time_ms=round(avg_time, 2),
            avg_top_score=round(avg_score, 3),
            avg_results_per_query=round(avg_results, 1),
        )
    
    def print_metrics(self):
        """Print formatted system metrics."""
        m = self.get_system_metrics()
        
        print("\n" + "="*50)
        print("SYSTEM METRICS")
        print("="*50)
        
        print("\n[Ingestion]")
        print(f"   Document Families: {m.total_families}")
        print(f"   Document Versions: {m.total_documents}")
        print(f"   Total Chunks: {m.total_chunks}")
        
        print("\n[Indexing]")
        print(f"   Vectors Indexed: {m.total_vectors}")
        
        print("\n[Query Performance]")
        print(f"   Total Queries: {m.total_queries}")
        print(f"   Avg Response Time: {m.avg_response_time_ms}ms")
        print(f"   Avg Top Score: {m.avg_top_score}")
        print(f"   Avg Results/Query: {m.avg_results_per_query}")
        
        print("="*50 + "\n")


class RAGEvaluator:
    """Evaluate RAG quality with test queries."""
    
    TEST_CASES = [
        {
            "query": "What are the side effects of Ozempic?",
            "expected_type": "safety",
            "expected_sections": ["adverse", "warning"],
            "min_score": 0.5,
        },
        {
            "query": "What is the dosage for Ozempic?",
            "expected_type": "dosing",
            "expected_sections": ["dosage", "administration"],
            "min_score": 0.5,
        },
        {
            "query": "What is Ozempic approved for?",
            "expected_type": "indication",
            "expected_sections": ["indication"],
            "min_score": 0.5,
        },
        {
            "query": "How does Ozempic work?",
            "expected_type": "mechanism",
            "expected_sections": ["pharmacology", "mechanism"],
            "min_score": 0.4,
        },
    ]
    
    def __init__(self):
        from app.services.rag import PharmaRetriever, classify_query
        self.retriever = PharmaRetriever()
        self.classify = classify_query
        self.sql_db = DocumentStore()
    
    def evaluate(self, verbose: bool = True) -> dict:
        """Run evaluation on test cases."""
        results = {
            "total": len(self.TEST_CASES),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        if verbose:
            print("\n" + "="*60)
            print("RAG EVALUATION")
            print("="*60)
        
        for i, test in enumerate(self.TEST_CASES, 1):
            if verbose:
                print(f"\n[{i}/{len(self.TEST_CASES)}] {test['query']}")
            
            start = time.time()
            try:
                search_results = self.retriever.retrieve(test["query"], top_k=5)
                elapsed_ms = int((time.time() - start) * 1000)
            except Exception as e:
                if verbose:
                    print(f"   [FAIL] Error: {e}")
                results["failed"] += 1
                results["details"].append({"query": test["query"], "error": str(e)})
                continue
            
            detected_type = self.classify(test["query"]).value
            type_match = detected_type == test["expected_type"]
            
            section_hits = 0
            for r in search_results:
                section_lower = r.section_title.lower()
                if any(s in section_lower for s in test["expected_sections"]):
                    section_hits += 1
            section_hit_rate = section_hits / len(search_results) if search_results else 0
            
            top_score = search_results[0].score if search_results else 0
            avg_score = sum(r.score for r in search_results) / len(search_results) if search_results else 0
            score_ok = top_score >= test["min_score"]
            
            passed = type_match and section_hit_rate >= 0.4 and score_ok
            
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            self.sql_db.log_query(
                query_id=str(uuid.uuid4()),
                query_text=test["query"],
                query_type=detected_type,
                num_results=len(search_results),
                top_score=top_score,
                avg_score=avg_score,
                response_time_ms=elapsed_ms
            )
            
            if verbose:
                status = "[PASS]" if passed else "[FAIL]"
                print(f"   {status} Type: {detected_type} (expected: {test['expected_type']})")
                print(f"      Scores: top={top_score:.3f}, avg={avg_score:.3f}")
                print(f"      Section hits: {section_hits}/{len(search_results)} ({section_hit_rate:.0%})")
                print(f"      Time: {elapsed_ms}ms")
            
            results["details"].append({
                "query": test["query"],
                "passed": passed,
                "type_match": type_match,
                "detected_type": detected_type,
                "top_score": top_score,
                "section_hit_rate": section_hit_rate,
                "time_ms": elapsed_ms,
            })
        
        pass_rate = results["passed"] / results["total"] if results["total"] > 0 else 0
        results["pass_rate"] = pass_rate
        
        if verbose:
            print("\n" + "-"*60)
            print(f"[Results] {results['passed']}/{results['total']} passed ({pass_rate:.0%})")
            print("="*60 + "\n")
        
        return results
    
    def evaluate_custom(self, queries: list[str], verbose: bool = True) -> dict:
        """Evaluate custom queries (no expected values, just metrics)."""
        results = []
        
        if verbose:
            print("\n[Custom Query Evaluation]")
            print("-"*40)
        
        for query in queries:
            start = time.time()
            search_results = self.retriever.retrieve(query, top_k=5)
            elapsed_ms = int((time.time() - start) * 1000)
            
            detected_type = self.classify(query).value
            top_score = search_results[0].score if search_results else 0
            avg_score = sum(r.score for r in search_results) / len(search_results) if search_results else 0
            
            self.sql_db.log_query(
                query_id=str(uuid.uuid4()),
                query_text=query,
                query_type=detected_type,
                num_results=len(search_results),
                top_score=top_score,
                avg_score=avg_score,
                response_time_ms=elapsed_ms
            )
            
            result = {
                "query": query,
                "type": detected_type,
                "num_results": len(search_results),
                "top_score": top_score,
                "avg_score": avg_score,
                "time_ms": elapsed_ms,
            }
            results.append(result)
            
            if verbose:
                print(f"\n> {query}")
                print(f"   Type: {detected_type}")
                print(f"   Results: {len(search_results)}, Top: {top_score:.3f}, Avg: {avg_score:.3f}")
                print(f"   Time: {elapsed_ms}ms")
        
        return {"queries": results}


def main():
    """Run evaluation and show metrics."""
    import sys
    
    args = sys.argv[1:]
    
    if "--metrics" in args:
        MetricsService().print_metrics()
    elif "--eval" in args:
        RAGEvaluator().evaluate(verbose=True)
    else:
        MetricsService().print_metrics()
        RAGEvaluator().evaluate(verbose=True)


if __name__ == "__main__":
    main()
