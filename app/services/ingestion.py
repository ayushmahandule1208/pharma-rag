"""
Ingestion Service - Download and process regulatory PDFs.
"""
import re
import uuid
import time
import requests
from pathlib import Path

import pdfplumber

from app.core import settings, file_hash, content_fingerprint, SECTION_KEYWORDS, PROTECTED_SECTIONS
from app.db import DocumentStore


# Sample drugs to download
SAMPLE_DRUGS = ["Ozempic", "Wegovy", "Keytruda", "Humira", "Eliquis"]


class IngestionService:
    """Download FDA labels and ingest into SQLite."""
    
    def __init__(self):
        self.input_dir = settings.RAW_DIR
        self.db = DocumentStore()
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
    
    def run(self, download: bool = True, force: bool = False) -> dict:
        """Full pipeline: download + ingest."""
        if download:
            print("\n[Download] Fetching FDA labels...")
            self._download_samples()
        
        print("\n[Ingest] Processing PDFs...")
        return self._ingest_all(force)
    
    def _download_samples(self, limit: int = 5):
        """Download sample FDA labels from DailyMed."""
        output_dir = self.input_dir / "FDA" / "LABEL"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for drug in SAMPLE_DRUGS[:limit]:
            path = output_dir / f"{drug}.pdf"
            if path.exists():
                print(f"   [skip] {drug} (exists)")
                continue
            
            try:
                resp = requests.get(
                    "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json",
                    params={"drug_name": drug}, timeout=30
                )
                data = resp.json().get("data", [])
                if not data:
                    print(f"   [fail] {drug} (not found)")
                    continue
                
                setid = data[0]["setid"]
                pdf_resp = requests.get(
                    f"https://dailymed.nlm.nih.gov/dailymed/downloadpdffile.cfm?setId={setid}",
                    timeout=60
                )
                path.write_bytes(pdf_resp.content)
                print(f"   [ok] {drug}")
                time.sleep(0.5)
            except Exception as e:
                print(f"   [fail] {drug}: {e}")
    
    def _ingest_all(self, force: bool = False) -> dict:
        """Ingest all PDFs from input directory."""
        pdfs = list(self.input_dir.rglob("*.pdf"))
        if not pdfs:
            print("   No PDFs found")
            return {"processed": 0}
        
        processed, skipped = 0, 0
        for pdf in pdfs:
            fhash = file_hash(pdf)
            if not force and self.db.is_processed(fhash):
                skipped += 1
                continue
            
            meta = self._parse_path(pdf)
            result = self._process_pdf(pdf, meta, fhash)
            print(f"   [ok] {pdf.name}: {result['saved']} chunks")
            processed += 1
        
        stats = self.db.get_stats()
        print(f"\n[Stats] {stats['documents']} docs, {stats['search_units']} chunks")
        return {"processed": processed, "skipped": skipped, **stats}
    
    def _parse_path(self, path: Path) -> dict:
        """Extract metadata from path structure."""
        parts = path.relative_to(self.input_dir).parts
        return {
            "drug_name": path.stem.replace("_", " ").title(),
            "authority": parts[0].upper() if len(parts) >= 2 else "FDA",
            "doc_type": parts[1].upper() if len(parts) >= 3 else "LABEL",
        }
    
    def _process_pdf(self, path: Path, meta: dict, fhash: str) -> dict:
        """Process single PDF through pipeline."""
        doc_id = str(uuid.uuid4())
        
        pages = self._extract_pdf(path)
        sections = self._detect_sections(pages)
        
        for s in sections:
            s["section_type"] = "general"
            title = s["section_title"].lower()
            for stype, keywords in SECTION_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    s["section_type"] = stype
                    break
        
        chunks = self._create_chunks(sections)
        
        units = []
        for c in chunks:
            if not (50 <= len(c["content"]) <= 10000):
                continue
            units.append({
                "unit_id": str(uuid.uuid4()),
                "section_number": c["section_number"],
                "section_title": c["section_title"],
                "section_type": c["section_type"],
                "content": c["content"],
                "fingerprint": content_fingerprint(c["content"]),
                "chunk_index": c["chunk_index"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
            })
        
        family_id = self.db.save_document(
            doc_id, fhash, str(path), 
            meta["drug_name"], meta["authority"], meta["doc_type"],
            version_date=meta.get("version_date")
        )
        saved, skipped = self.db.save_units(units, doc_id, family_id)
        
        return {"saved": saved, "skipped": skipped}
    
    def _extract_pdf(self, path: Path) -> list[dict]:
        """Extract text from PDF."""
        pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append({"page": i, "text": text})
        return pages
    
    def _detect_sections(self, pages: list[dict]) -> list[dict]:
        """Find section headers."""
        pattern = re.compile(r'^(\d+(?:\.\d+)*)\s+([A-Z][A-Z\s,&\-]+)$')
        sections, current = [], None
        
        for page in pages:
            for line in page["text"].split("\n"):
                line = line.strip()
                if not line:
                    continue
                match = pattern.match(line)
                if match:
                    if current:
                        sections.append(current)
                    current = {
                        "section_number": match.group(1),
                        "section_title": match.group(2).strip().title(),
                        "content": "",
                        "page_start": page["page"],
                        "page_end": page["page"],
                    }
                elif current:
                    current["content"] += line + " "
                    current["page_end"] = page["page"]
        
        if current:
            sections.append(current)
        return sections
    
    def _create_chunks(self, sections: list[dict]) -> list[dict]:
        """Split sections into chunks."""
        chunks = []
        for s in sections:
            content = s["content"].strip()
            if s["section_title"] in PROTECTED_SECTIONS or len(content) <= self.chunk_size:
                chunks.append({**s, "chunk_index": 0})
                continue
            
            step = self.chunk_size - self.chunk_overlap
            for idx, start in enumerate(range(0, len(content), step)):
                chunks.append({**s, "content": content[start:start + self.chunk_size], "chunk_index": idx})
        return chunks
