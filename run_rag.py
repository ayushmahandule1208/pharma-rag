"""
Run the complete RAG pipeline.

Usage:
    python run_rag.py                    # Full pipeline: download + ingest + index + query
    python run_rag.py --index            # Just index existing chunks to vector DB
    python run_rag.py --query "question" # Query without interactive mode
    python run_rag.py --interactive      # Interactive query mode
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    args = sys.argv[1:]
    
    # Index only
    if "--index" in args:
        from app.db import VectorStore
        vs = VectorStore()
        vs.index_all()
        print(f"\n[Stats] Vectors indexed: {vs.get_stats()['total_vectors']}")
        return
    
    # Single query
    if "--query" in args:
        idx = args.index("--query")
        if idx + 1 < len(args):
            question = args[idx + 1]
            from app.services import PharmaRAG
            rag = PharmaRAG()
            result = rag.query(question)
            print(f"\n[Type: {result['query_type']}]")
            print(f"\n{result['answer']}")
        return
    
    # Interactive mode
    if "--interactive" in args:
        from app.services.rag import main as rag_main
        rag_main()
        return
    
    # Full pipeline (default)
    print("\n" + "="*60)
    print("PHARMA RAG - FULL PIPELINE")
    print("="*60)
    
    # Step 1: Ingest
    print("\n[Step 1] Ingestion")
    from app.services import IngestionService
    IngestionService().run(download=True)
    
    # Step 2: Index
    print("\n[Step 2] Vector Indexing")
    from app.db import VectorStore
    vs = VectorStore()
    vs.index_all()
    print(f"   [ok] {vs.get_stats()['total_vectors']} vectors")
    
    # Step 3: Interactive query
    print("\n[Step 3] Query Interface")
    print("-"*60)
    
    from app.services import PharmaRAG
    from app.core.config import API_KEYS
    rag = PharmaRAG()
    
    if not API_KEYS:
        print("[warn] No API keys - using fallback responses")
    else:
        print(f"[ok] {len(API_KEYS)} API keys loaded")
    
    print("\nType your question (or 'quit' to exit):\n")
    
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            break
        
        if question.lower() in ["quit", "exit", "q", ""]:
            break
        
        result = rag.query(question)
        print(f"\n[Type: {result['query_type']}]")
        print(f"\n{result['answer']}")
        print("\n" + "-"*50 + "\n")
    
    print("\n[Done]")


if __name__ == "__main__":
    main()
