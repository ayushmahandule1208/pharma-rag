"""
Run evaluation and metrics.

Usage:
    python run_eval.py              # Show metrics + run evaluation
    python run_eval.py --metrics    # Show metrics only
    python run_eval.py --eval       # Run evaluation only
    python run_eval.py --versions   # Show document versions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


def show_versions():
    """Show all document families and versions."""
    from app.db import DocumentStore
    db = DocumentStore()
    
    families = db.get_families()
    
    print("\n" + "="*60)
    print("DOCUMENT FAMILIES & VERSIONS")
    print("="*60)
    
    if not families:
        print("\nNo documents ingested yet.")
        return
    
    for f in families:
        print(f"\n[Family] {f['family_id']}")
        print(f"   Drug: {f['drug_name']}")
        print(f"   Authority: {f['authority']}")
        print(f"   Versions: {f['version_count']}")
        
        versions = db.get_versions(f['family_id'])
        for v in versions:
            latest = "[LATEST]" if v['is_latest'] else ""
            date = v['version_date'] or "unknown"
            print(f"      v{v['version_num']}: {date} {latest}")
            if v['supersedes']:
                print(f"         -> supersedes: {v['supersedes'][:8]}...")
    
    print("\n" + "="*60)


def main():
    args = sys.argv[1:]
    
    if "--versions" in args:
        show_versions()
        return
    
    if "--metrics" in args:
        from app.services import MetricsService
        MetricsService().print_metrics()
        return
    
    if "--eval" in args:
        from app.services import RAGEvaluator
        RAGEvaluator().evaluate(verbose=True)
        return
    
    # Default: show all
    from app.services import MetricsService, RAGEvaluator
    
    MetricsService().print_metrics()
    
    print("\nRun evaluation? (y/n): ", end="")
    try:
        if input().strip().lower() == "y":
            RAGEvaluator().evaluate(verbose=True)
    except EOFError:
        pass


if __name__ == "__main__":
    main()
