"""
Vector Store - FAISS implementation for Hugging Face Spaces deployment.
Lightweight, in-memory vector search.
"""
import os
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

from app.core import settings
from app.db.document_store import DocumentStore


class VectorStore:
    """FAISS-based vector store for pharma RAG."""
    
    def __init__(self):
        self.index_path = settings.DATA_DIR / "faiss_index"
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Storage
        self.vectors = []
        self.metadata = []
        self.documents = []
        self.ids = []
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self):
        """Load index from disk if exists."""
        index_file = self.index_path / "index.pkl"
        if index_file.exists():
            with open(index_file, "rb") as f:
                data = pickle.load(f)
                self.vectors = data.get("vectors", [])
                self.metadata = data.get("metadata", [])
                self.documents = data.get("documents", [])
                self.ids = data.get("ids", [])
    
    def _save_index(self):
        """Save index to disk."""
        index_file = self.index_path / "index.pkl"
        with open(index_file, "wb") as f:
            pickle.dump({
                "vectors": self.vectors,
                "metadata": self.metadata,
                "documents": self.documents,
                "ids": self.ids,
            }, f)
    
    def embed_text(self, text: str) -> list[float]:
        """Convert text to vector."""
        return self.embedder.encode(text).tolist()
    
    def index_all(self, force: bool = False):
        """Index all chunks from SQLite."""
        sql_db = DocumentStore()
        units = sql_db.get_units()
        
        if not units:
            print("No chunks to index")
            return
        
        existing_ids = set(self.ids)
        
        to_add = []
        for u in units:
            if not force and u["unit_id"] in existing_ids:
                continue
            to_add.append(u)
        
        if not to_add:
            print(f"All {len(units)} chunks already indexed")
            return
        
        print(f"[Index] Indexing {len(to_add)} chunks...")
        
        # Batch encode
        texts = [u["content"] for u in to_add]
        embeddings = self.embedder.encode(texts, show_progress_bar=True)
        
        for i, u in enumerate(to_add):
            self.ids.append(u["unit_id"])
            self.vectors.append(embeddings[i].tolist())
            self.documents.append(u["content"])
            self.metadata.append({
                "doc_id": u["doc_id"],
                "section_title": u["section_title"],
                "section_type": u["section_type"],
                "section_number": u["section_number"],
                "page_start": u["page_start"],
                "page_end": u["page_end"],
                "chunk_index": u["chunk_index"],
            })
        
        # Save to disk
        self._save_index()
        print(f"[Done] Indexed {len(to_add)} chunks (total: {len(self.ids)})")
    
    def search(self, query: str, top_k: int = 10, filters: dict = None) -> list[dict]:
        """Search for similar chunks using cosine similarity."""
        if not self.vectors:
            return []
        
        query_embedding = np.array(self.embed_text(query))
        vectors_array = np.array(self.vectors)
        
        # Cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        vectors_norm = vectors_array / np.linalg.norm(vectors_array, axis=1, keepdims=True)
        similarities = np.dot(vectors_norm, query_norm)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            # Apply filters if provided
            if filters:
                match = all(
                    self.metadata[idx].get(k) == v 
                    for k, v in filters.items()
                )
                if not match:
                    continue
            
            results.append({
                "id": self.ids[idx],
                "text": self.documents[idx],
                "score": float(similarities[idx]),
                "metadata": self.metadata[idx]
            })
        
        return results
    
    def get_stats(self) -> dict:
        """Get vector store stats."""
        return {
            "total_vectors": len(self.ids)
        }

