"""
Vector Store - ChromaDB wrapper for semantic search.
"""
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer

from app.core import settings
from app.db import DocumentStore


class VectorStore:
    """Simple ChromaDB wrapper for pharma RAG."""
    
    def __init__(self):
        self.db_path = settings.DATA_DIR / "vectordb"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection = self.client.get_or_create_collection(
            name="pharma_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    def embed_text(self, text: str) -> list[float]:
        """Convert text to vector."""
        return self.embedder.encode(text).tolist()
    
    def index_all(self, force: bool = False):
        """Index all chunks from SQLite into ChromaDB."""
        sql_db = DocumentStore()
        units = sql_db.get_units()
        
        if not units:
            print("No chunks to index")
            return
        
        existing_ids = set(self.collection.get()["ids"])
        
        to_add = []
        for u in units:
            if not force and u["unit_id"] in existing_ids:
                continue
            to_add.append(u)
        
        if not to_add:
            print(f"All {len(units)} chunks already indexed")
            return
        
        print(f"[Index] Indexing {len(to_add)} chunks...")
        
        batch_size = 100
        for i in range(0, len(to_add), batch_size):
            batch = to_add[i:i + batch_size]
            
            texts = [u["content"] for u in batch]
            embeddings = self.embedder.encode(texts).tolist()
            
            self.collection.add(
                ids=[u["unit_id"] for u in batch],
                embeddings=embeddings,
                documents=texts,
                metadatas=[{
                    "doc_id": u["doc_id"],
                    "section_title": u["section_title"],
                    "section_type": u["section_type"],
                    "section_number": u["section_number"],
                    "page_start": u["page_start"],
                    "page_end": u["page_end"],
                    "chunk_index": u["chunk_index"],
                } for u in batch]
            )
            print(f"   [ok] {min(i + batch_size, len(to_add))}/{len(to_add)}")
        
        print(f"[Done] Indexed {len(to_add)} chunks")
    
    def search(self, query: str, top_k: int = 10, filters: dict = None) -> list[dict]:
        """Search for similar chunks."""
        query_embedding = self.embed_text(query)
        
        where = None
        if filters:
            where = filters
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "score": 1 - results["distances"][0][i],
                "metadata": results["metadatas"][0][i]
            })
        
        return formatted
    
    def get_stats(self) -> dict:
        """Get vector store stats."""
        return {
            "total_vectors": self.collection.count()
        }
