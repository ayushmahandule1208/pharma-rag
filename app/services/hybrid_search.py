"""
Hybrid Search Engine - BM25 + Vector Search with Re-ranking

Industry-standard retrieval pipeline:
1. BM25 (keyword matching) - catches exact terms
2. Vector Search (semantic) - catches meaning
3. Reciprocal Rank Fusion - merges results
4. Cross-Encoder Re-ranking - improves top results
"""
import re
import math
import numpy as np
from dataclasses import dataclass
from typing import Optional
from collections import Counter

from sentence_transformers import SentenceTransformer, CrossEncoder

from app.db.document_store import DocumentStore
from app.core import settings


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SearchResult:
    """Search result with all metadata."""
    unit_id: str
    doc_id: str
    content: str
    section_title: str
    section_type: str
    page_start: int
    page_end: int
    
    # Scores
    bm25_score: float = 0.0
    vector_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    
    # Document metadata (enriched)
    drug_name: str = ""
    authority: str = "FDA"


# =============================================================================
# BM25 IMPLEMENTATION
# =============================================================================

class BM25Index:
    """
    BM25 (Best Matching 25) keyword search.
    
    Industry-standard keyword matching algorithm that considers:
    - Term frequency (TF)
    - Inverse document frequency (IDF) 
    - Document length normalization
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: Term frequency saturation parameter (1.2-2.0 typical)
            b: Length normalization (0.75 typical)
        """
        self.k1 = k1
        self.b = b
        
        # Index data
        self.documents = []  # Original documents
        self.doc_ids = []    # Document IDs
        self.metadata = []   # Document metadata
        
        # Tokenized data
        self.tokenized_docs = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        
        # IDF cache
        self.idf_cache = {}
        self.doc_count = 0
    
    def tokenize(self, text: str) -> list[str]:
        """
        Simple tokenizer - lowercase, split on non-alphanumeric.
        Keeps medical terms intact.
        """
        text = text.lower()
        # Split on whitespace and punctuation, keep alphanumeric
        tokens = re.findall(r'\b[a-z0-9]+\b', text)
        return tokens
    
    def build_index(self, documents: list[dict]):
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of dicts with 'unit_id', 'content', and metadata
        """
        self.documents = []
        self.doc_ids = []
        self.metadata = []
        self.tokenized_docs = []
        self.doc_lengths = []
        
        for doc in documents:
            self.documents.append(doc['content'])
            self.doc_ids.append(doc['unit_id'])
            self.metadata.append({
                'doc_id': doc.get('doc_id', ''),
                'section_title': doc.get('section_title', ''),
                'section_type': doc.get('section_type', ''),
                'page_start': doc.get('page_start', 0),
                'page_end': doc.get('page_end', 0),
            })
            
            tokens = self.tokenize(doc['content'])
            self.tokenized_docs.append(tokens)
            self.doc_lengths.append(len(tokens))
        
        self.doc_count = len(self.documents)
        self.avg_doc_length = sum(self.doc_lengths) / max(self.doc_count, 1)
        
        # Precompute IDF for all terms
        self._compute_idf()
    
    def _compute_idf(self):
        """Compute IDF for all terms in corpus."""
        # Count documents containing each term
        doc_freq = Counter()
        for tokens in self.tokenized_docs:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1
        
        # Compute IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        for term, df in doc_freq.items():
            numerator = self.doc_count - df + 0.5
            denominator = df + 0.5
            self.idf_cache[term] = math.log(numerator / denominator + 1)
    
    def get_scores(self, query: str) -> list[float]:
        """
        Compute BM25 scores for all documents.
        
        Returns:
            List of scores (same order as documents)
        """
        query_tokens = self.tokenize(query)
        scores = [0.0] * self.doc_count
        
        for token in query_tokens:
            idf = self.idf_cache.get(token, 0)
            
            for i, doc_tokens in enumerate(self.tokenized_docs):
                # Term frequency in document
                tf = doc_tokens.count(token)
                if tf == 0:
                    continue
                
                # Length normalization
                doc_len = self.doc_lengths[i]
                len_norm = 1 - self.b + self.b * (doc_len / self.avg_doc_length)
                
                # BM25 score for this term
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * len_norm
                scores[i] += idf * (numerator / denominator)
        
        return scores
    
    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Search with BM25.
        
        Returns:
            List of dicts with 'id', 'content', 'score', 'metadata'
        """
        if not self.documents:
            return []
        
        scores = self.get_scores(query)
        
        # Get top-k indices
        scored_indices = [(i, s) for i, s in enumerate(scores) if s > 0]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        top_indices = scored_indices[:top_k]
        
        results = []
        for idx, score in top_indices:
            results.append({
                'id': self.doc_ids[idx],
                'content': self.documents[idx],
                'score': score,
                'metadata': self.metadata[idx]
            })
        
        return results


# =============================================================================
# HYBRID SEARCH ENGINE
# =============================================================================

class HybridSearchEngine:
    """
    Production-grade hybrid search with:
    - BM25 keyword matching
    - Dense vector similarity
    - Reciprocal Rank Fusion
    - Cross-Encoder re-ranking
    """
    
    def __init__(self, use_reranker: bool = True):
        """
        Args:
            use_reranker: Whether to use cross-encoder re-ranking
        """
        self.db = DocumentStore()
        
        # Embedding model (same as vector store)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.dimension = 384
        
        # Cross-encoder for re-ranking (lightweight model)
        self.use_reranker = use_reranker
        self.reranker = None
        if use_reranker:
            try:
                self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                print("[HybridSearch] Cross-encoder reranker loaded")
            except Exception as e:
                print(f"[HybridSearch] Reranker not available: {e}")
                self.use_reranker = False
        
        # BM25 index
        self.bm25 = BM25Index()
        
        # Vector index (in-memory for speed)
        self.vectors = []
        self.vector_ids = []
        self.vector_metadata = []
        self.vector_documents = []
        
        # Document cache
        self.doc_cache = {}
        
        # Build indices
        self._build_indices()
    
    def _build_indices(self):
        """Build both BM25 and vector indices from database."""
        units = self.db.get_units()
        
        if not units:
            print("[HybridSearch] No documents to index")
            return
        
        print(f"[HybridSearch] Building indices for {len(units)} chunks...")
        
        # Build BM25 index
        self.bm25.build_index(units)
        
        # Build vector index
        texts = [u['content'] for u in units]
        embeddings = self.embedder.encode(texts, show_progress_bar=True, batch_size=32)
        
        for i, unit in enumerate(units):
            self.vector_ids.append(unit['unit_id'])
            self.vectors.append(embeddings[i])
            self.vector_documents.append(unit['content'])
            self.vector_metadata.append({
                'doc_id': unit['doc_id'],
                'section_title': unit['section_title'],
                'section_type': unit['section_type'],
                'page_start': unit['page_start'],
                'page_end': unit['page_end'],
            })
        
        self.vectors = np.array(self.vectors)
        print(f"[HybridSearch] Indices built: {len(units)} documents")
    
    def rebuild_indices(self):
        """Rebuild indices (call after adding new documents)."""
        self.vectors = []
        self.vector_ids = []
        self.vector_metadata = []
        self.vector_documents = []
        self.doc_cache = {}
        self._build_indices()
    
    def _get_doc_info(self, doc_id: str) -> dict:
        """Get document metadata from cache or database."""
        if doc_id not in self.doc_cache:
            with self.db._conn() as conn:
                row = conn.execute(
                    "SELECT drug_name, authority FROM documents WHERE doc_id=?",
                    (doc_id,)
                ).fetchone()
                self.doc_cache[doc_id] = dict(row) if row else {'drug_name': 'Unknown', 'authority': 'FDA'}
        return self.doc_cache[doc_id]
    
    def semantic_search(self, query: str, top_k: int = 20) -> list[dict]:
        """
        Dense vector similarity search.
        
        Returns results with cosine similarity scores.
        """
        if len(self.vectors) == 0:
            return []
        
        # Embed query
        query_vec = self.embedder.encode(query)
        query_norm = query_vec / np.linalg.norm(query_vec)
        
        # Compute cosine similarities
        vectors_norm = self.vectors / np.linalg.norm(self.vectors, axis=1, keepdims=True)
        similarities = np.dot(vectors_norm, query_norm)
        
        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                'id': self.vector_ids[idx],
                'content': self.vector_documents[idx],
                'score': float(similarities[idx]),
                'metadata': self.vector_metadata[idx]
            })
        
        return results
    
    def keyword_search(self, query: str, top_k: int = 20) -> list[dict]:
        """
        BM25 keyword search.
        
        Returns results with BM25 scores.
        """
        return self.bm25.search(query, top_k=top_k)
    
    def reciprocal_rank_fusion(
        self, 
        semantic_results: list[dict], 
        keyword_results: list[dict],
        k: int = 60
    ) -> list[dict]:
        """
        Merge results using Reciprocal Rank Fusion.
        
        RRF Score = sum(1 / (k + rank_i)) for each result list
        
        Args:
            k: Ranking constant (60 is standard)
        
        Returns:
            Merged and ranked results
        """
        scores = {}
        result_data = {}
        
        # Process semantic results
        for rank, result in enumerate(semantic_results):
            doc_id = result['id']
            rrf_score = 1.0 / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            
            if doc_id not in result_data:
                result_data[doc_id] = {
                    'id': doc_id,
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'semantic_score': result['score'],
                    'bm25_score': 0.0,
                    'semantic_rank': rank + 1,
                    'bm25_rank': None
                }
            else:
                result_data[doc_id]['semantic_score'] = result['score']
                result_data[doc_id]['semantic_rank'] = rank + 1
        
        # Process keyword results
        for rank, result in enumerate(keyword_results):
            doc_id = result['id']
            rrf_score = 1.0 / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            
            if doc_id not in result_data:
                result_data[doc_id] = {
                    'id': doc_id,
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'semantic_score': 0.0,
                    'bm25_score': result['score'],
                    'semantic_rank': None,
                    'bm25_rank': rank + 1
                }
            else:
                result_data[doc_id]['bm25_score'] = result['score']
                result_data[doc_id]['bm25_rank'] = rank + 1
        
        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        merged = []
        for doc_id in sorted_ids:
            data = result_data[doc_id]
            data['fusion_score'] = scores[doc_id]
            merged.append(data)
        
        return merged
    
    def rerank(self, query: str, results: list[dict], top_k: int = 10) -> list[dict]:
        """
        Re-rank results using cross-encoder.
        
        Cross-encoder sees (query, document) pairs and produces
        more accurate relevance scores than bi-encoders.
        """
        if not self.use_reranker or not self.reranker or not results:
            return results[:top_k]
        
        # Prepare pairs
        pairs = [[query, r['content']] for r in results]
        
        # Score with cross-encoder
        scores = self.reranker.predict(pairs)
        
        # Add scores and sort
        for i, result in enumerate(results):
            result['rerank_score'] = float(scores[i])
        
        results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return results[:top_k]
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        use_rerank: bool = True,
        semantic_weight: float = 0.5,
        return_details: bool = False
    ) -> list[SearchResult]:
        """
        Full hybrid search pipeline.
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_rerank: Whether to apply cross-encoder re-ranking
            semantic_weight: Weight for semantic vs keyword (0.5 = equal)
            return_details: Include detailed scoring info
        
        Returns:
            List of SearchResult objects
        """
        # Step 1: Get results from both methods
        semantic_results = self.semantic_search(query, top_k=top_k * 4)
        keyword_results = self.keyword_search(query, top_k=top_k * 4)
        
        # Step 2: Merge with RRF
        merged = self.reciprocal_rank_fusion(semantic_results, keyword_results)
        
        # Step 3: Re-rank top candidates (if enabled)
        if use_rerank and self.use_reranker:
            # Re-rank more than we need, then take top_k
            reranked = self.rerank(query, merged[:top_k * 2], top_k=top_k)
        else:
            reranked = merged[:top_k]
        
        # Step 4: Convert to SearchResult objects with document enrichment
        results = []
        for r in reranked:
            doc_info = self._get_doc_info(r['metadata']['doc_id'])
            
            # Compute final score
            if 'rerank_score' in r:
                final_score = r['rerank_score']
            else:
                final_score = r['fusion_score']
            
            results.append(SearchResult(
                unit_id=r['id'],
                doc_id=r['metadata']['doc_id'],
                content=r['content'],
                section_title=r['metadata']['section_title'],
                section_type=r['metadata']['section_type'],
                page_start=r['metadata']['page_start'],
                page_end=r['metadata']['page_end'],
                bm25_score=r.get('bm25_score', 0.0),
                vector_score=r.get('semantic_score', 0.0),
                fusion_score=r.get('fusion_score', 0.0),
                rerank_score=r.get('rerank_score', 0.0),
                final_score=final_score,
                drug_name=doc_info.get('drug_name', 'Unknown'),
                authority=doc_info.get('authority', 'FDA')
            ))
        
        return results
    
    def get_stats(self) -> dict:
        """Get search engine statistics."""
        return {
            'total_documents': len(self.vector_ids),
            'bm25_indexed': len(self.bm25.documents),
            'vector_indexed': len(self.vectors),
            'reranker_enabled': self.use_reranker,
            'embedding_model': 'all-MiniLM-L6-v2',
            'reranker_model': 'cross-encoder/ms-marco-MiniLM-L-6-v2' if self.use_reranker else None
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_hybrid_engine = None

def get_hybrid_engine(use_reranker: bool = True) -> HybridSearchEngine:
    """Get or create singleton hybrid search engine."""
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridSearchEngine(use_reranker=use_reranker)
    return _hybrid_engine

