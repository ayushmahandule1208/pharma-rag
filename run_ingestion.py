"""
Run ingestion: python run_ingestion.py [--no-download] [--force] [--stats]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services import IngestionService
from app.db import DocumentStore

if __name__ == "__main__":
    if "--stats" in sys.argv:
        stats = DocumentStore().get_stats()
        print(f"\n[Stats] {stats['documents']} docs, {stats['search_units']} chunks\n")
    else:
        IngestionService().run(
            download="--no-download" not in sys.argv,
            force="--force" in sys.argv
        )
