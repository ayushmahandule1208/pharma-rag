"""SQLite Document Store with Version Tracking."""
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from app.core import settings


class DocumentStore:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or settings.DATA_DIR / "pharma_rag.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                -- Document families (groups versions together)
                CREATE TABLE IF NOT EXISTS document_families (
                    family_id TEXT PRIMARY KEY,
                    drug_name TEXT,
                    authority TEXT,
                    doc_type TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Documents (each PDF is a version)
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    family_id TEXT,
                    file_hash TEXT UNIQUE,
                    file_path TEXT,
                    drug_name TEXT,
                    authority TEXT,
                    doc_type TEXT,
                    version_num INTEGER DEFAULT 1,
                    version_date TEXT,
                    is_latest INTEGER DEFAULT 1,
                    supersedes TEXT,
                    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (family_id) REFERENCES document_families(family_id)
                );
                
                -- Search units (chunks)
                CREATE TABLE IF NOT EXISTS search_units (
                    unit_id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    family_id TEXT,
                    section_number TEXT,
                    section_title TEXT,
                    section_type TEXT,
                    content TEXT,
                    fingerprint TEXT,
                    chunk_index INTEGER,
                    page_start INTEGER,
                    page_end INTEGER,
                    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
                );
                
                -- Fingerprints for dedup
                CREATE TABLE IF NOT EXISTS fingerprints (
                    fingerprint TEXT PRIMARY KEY,
                    first_doc_id TEXT,
                    first_family_id TEXT
                );
                
                -- Query logs for evaluation
                CREATE TABLE IF NOT EXISTS query_logs (
                    query_id TEXT PRIMARY KEY,
                    query_text TEXT,
                    query_type TEXT,
                    num_results INTEGER,
                    top_score REAL,
                    avg_score REAL,
                    response_time_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_docs_family ON documents(family_id);
                CREATE INDEX IF NOT EXISTS idx_units_doc ON search_units(doc_id);
                CREATE INDEX IF NOT EXISTS idx_units_family ON search_units(family_id);
            """)
    
    # =========================================================================
    # VERSION TRACKING
    # =========================================================================
    
    def get_or_create_family(self, drug_name: str, authority: str, doc_type: str) -> str:
        """Get existing family or create new one."""
        family_id = f"{authority}_{doc_type}_{drug_name}".replace(" ", "_").upper()
        
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT family_id FROM document_families WHERE family_id=?", (family_id,)
            ).fetchone()
            
            if not existing:
                conn.execute(
                    "INSERT INTO document_families (family_id, drug_name, authority, doc_type) VALUES (?,?,?,?)",
                    (family_id, drug_name, authority, doc_type)
                )
            
            return family_id
    
    def is_processed(self, file_hash: str) -> bool:
        with self._conn() as conn:
            return conn.execute(
                "SELECT 1 FROM documents WHERE file_hash=?", (file_hash,)
            ).fetchone() is not None
    
    def save_document(self, doc_id: str, file_hash: str, file_path: str,
                      drug_name: str, authority: str, doc_type: str, version_date: str = None):
        """Save document with version tracking."""
        family_id = self.get_or_create_family(drug_name, authority, doc_type)
        
        with self._conn() as conn:
            # Mark previous versions as not latest
            conn.execute(
                "UPDATE documents SET is_latest=0 WHERE family_id=?", (family_id,)
            )
            
            # Get version number
            row = conn.execute(
                "SELECT MAX(version_num) FROM documents WHERE family_id=?", (family_id,)
            ).fetchone()
            version_num = (row[0] or 0) + 1
            
            # Get previous version for supersedes link
            prev = conn.execute(
                "SELECT doc_id FROM documents WHERE family_id=? AND version_num=?",
                (family_id, version_num - 1)
            ).fetchone()
            supersedes = prev[0] if prev else None
            
            conn.execute("""
                INSERT INTO documents 
                (doc_id, family_id, file_hash, file_path, drug_name, authority, doc_type, 
                 version_num, version_date, supersedes)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (doc_id, family_id, file_hash, file_path, drug_name, authority, doc_type,
                  version_num, version_date, supersedes))
            
            return family_id
    
    def get_versions(self, family_id: str) -> list[dict]:
        """Get all versions of a document family."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE family_id=? ORDER BY version_num DESC",
                (family_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    def get_latest_version(self, family_id: str) -> dict:
        """Get latest version of a document family."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE family_id=? AND is_latest=1",
                (family_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def get_families(self) -> list[dict]:
        """Get all document families with version counts."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT f.*, COUNT(d.doc_id) as version_count,
                       MAX(d.version_date) as latest_date
                FROM document_families f
                LEFT JOIN documents d ON f.family_id = d.family_id
                GROUP BY f.family_id
            """).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # SEARCH UNITS
    # =========================================================================
    
    def save_units(self, units: list[dict], doc_id: str, family_id: str = None) -> tuple[int, int]:
        """Save units, skip duplicates. Returns (saved, skipped)."""
        saved, skipped = 0, 0
        with self._conn() as conn:
            # Get family_id if not provided
            if not family_id:
                row = conn.execute("SELECT family_id FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
                family_id = row[0] if row else None
            
            for u in units:
                fp = u["fingerprint"]
                if conn.execute("SELECT 1 FROM fingerprints WHERE fingerprint=?", (fp,)).fetchone():
                    skipped += 1
                    continue
                conn.execute(
                    "INSERT INTO fingerprints (fingerprint, first_doc_id, first_family_id) VALUES (?,?,?)",
                    (fp, doc_id, family_id)
                )
                conn.execute("""
                    INSERT INTO search_units (unit_id, doc_id, family_id, section_number, section_title, 
                        section_type, content, fingerprint, chunk_index, page_start, page_end)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (u["unit_id"], doc_id, family_id, u["section_number"], u["section_title"],
                      u["section_type"], u["content"], fp, u["chunk_index"], u["page_start"], u["page_end"]))
                saved += 1
        return saved, skipped
    
    def get_units(self, doc_id: str = None, family_id: str = None, latest_only: bool = False) -> list[dict]:
        """Get search units with filtering options."""
        with self._conn() as conn:
            if doc_id:
                rows = conn.execute("SELECT * FROM search_units WHERE doc_id=?", (doc_id,)).fetchall()
            elif family_id:
                if latest_only:
                    # Get units from latest version only
                    rows = conn.execute("""
                        SELECT su.* FROM search_units su
                        JOIN documents d ON su.doc_id = d.doc_id
                        WHERE su.family_id=? AND d.is_latest=1
                    """, (family_id,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM search_units WHERE family_id=?", (family_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM search_units").fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # QUERY LOGGING (for evaluation)
    # =========================================================================
    
    def log_query(self, query_id: str, query_text: str, query_type: str,
                  num_results: int, top_score: float, avg_score: float, response_time_ms: int):
        """Log a query for evaluation."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO query_logs (query_id, query_text, query_type, num_results, 
                    top_score, avg_score, response_time_ms)
                VALUES (?,?,?,?,?,?,?)
            """, (query_id, query_text, query_type, num_results, top_score, avg_score, response_time_ms))
    
    def get_query_logs(self, limit: int = 100) -> list[dict]:
        """Get recent query logs."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM query_logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> dict:
        with self._conn() as conn:
            return {
                "families": conn.execute("SELECT COUNT(*) FROM document_families").fetchone()[0],
                "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                "search_units": conn.execute("SELECT COUNT(*) FROM search_units").fetchone()[0],
                "queries_logged": conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0],
            }
