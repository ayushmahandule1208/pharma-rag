"""
FDA Drug Label PDF Downloader
Downloads drug labels from DailyMed for the PharmaRAG system.
"""

import requests
import time
from pathlib import Path
import re

# Target directory for PDFs
OUTPUT_DIR = Path("data/raw/FDA/LABEL")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# DailyMed API endpoints
DAILYMED_SEARCH = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
DAILYMED_PDF = "https://dailymed.nlm.nih.gov/dailymed/downloadpdffile.cfm"

# Drugs to download (20 new ones to complement existing 5)
DRUGS_TO_DOWNLOAD = [
    # Drug name, search term (for better matching)
    ("Jardiance", "jardiance"),
    ("Entresto", "entresto"),
    ("Dupixent", "dupixent"),
    ("Stelara", "stelara"),
    ("Opdivo", "opdivo"),
    ("Xarelto", "xarelto"),
    ("Trulicity", "trulicity"),
    ("Skyrizi", "skyrizi"),
    ("Rinvoq", "rinvoq"),
    ("Cosentyx", "cosentyx"),
    ("Enbrel", "enbrel"),
    ("Tecfidera", "tecfidera"),
    ("Ocrevus", "ocrevus"),
    ("Tremfya", "tremfya"),
    ("Taltz", "taltz"),
    ("Otezla", "otezla"),
    ("Rybelsus", "rybelsus"),
    ("Mounjaro", "mounjaro"),
    ("Repatha", "repatha"),
    ("Praluent", "praluent"),
]


def search_drug(drug_name: str) -> str | None:
    """Search DailyMed for a drug and return the setid."""
    try:
        params = {
            "drug_name": drug_name,
            "pagesize": 10,
        }
        response = requests.get(DAILYMED_SEARCH, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])
        
        if not results:
            print(f"  [!] No results found for {drug_name}")
            return None
        
        # Find the best match (prefer exact brand name match)
        for result in results:
            title = result.get("title", "").upper()
            if drug_name.upper() in title:
                setid = result.get("setid")
                print(f"  [OK] Found: {result.get('title', 'Unknown')[:60]}...")
                return setid
        
        # If no exact match, use first result
        setid = results[0].get("setid")
        print(f"  [~] Using: {results[0].get('title', 'Unknown')[:60]}...")
        return setid
        
    except Exception as e:
        print(f"  [X] Search error: {e}")
        return None


def download_pdf(setid: str, drug_name: str) -> bool:
    """Download PDF for a given setid."""
    try:
        # DailyMed PDF download URL
        pdf_url = f"https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid={setid}&type=display"
        
        # First, get the actual PDF URL from the page
        # DailyMed uses a redirect, so we need to follow it
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Try direct PDF download
        pdf_direct_url = f"https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid={setid}&type=pdf"
        
        response = requests.get(pdf_direct_url, headers=headers, timeout=60, allow_redirects=True)
        
        # Check if we got a PDF
        content_type = response.headers.get("Content-Type", "")
        
        if "pdf" in content_type.lower() or response.content[:4] == b'%PDF':
            output_path = OUTPUT_DIR / f"{drug_name}.pdf"
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            size_kb = len(response.content) / 1024
            print(f"  [OK] Downloaded: {output_path.name} ({size_kb:.1f} KB)")
            return True
        else:
            # Try alternative method - SPL to PDF
            alt_url = f"https://dailymed.nlm.nih.gov/dailymed/downloadpdffile.cfm?setId={setid}"
            response = requests.get(alt_url, headers=headers, timeout=60, allow_redirects=True)
            
            if response.content[:4] == b'%PDF':
                output_path = OUTPUT_DIR / f"{drug_name}.pdf"
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                size_kb = len(response.content) / 1024
                print(f"  [OK] Downloaded: {output_path.name} ({size_kb:.1f} KB)")
                return True
            
            print(f"  [!] Could not get PDF (got {content_type})")
            return False
            
    except Exception as e:
        print(f"  [X] Download error: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("FDA Drug Label PDF Downloader")
    print("=" * 60)
    print(f"\nTarget directory: {OUTPUT_DIR.absolute()}")
    print(f"Drugs to download: {len(DRUGS_TO_DOWNLOAD)}")
    print("-" * 60)
    
    # Check existing files
    existing = {f.stem.lower() for f in OUTPUT_DIR.glob("*.pdf")}
    print(f"Existing PDFs: {len(existing)}")
    
    success = 0
    failed = []
    skipped = []
    
    for drug_name, search_term in DRUGS_TO_DOWNLOAD:
        print(f"\n[{drug_name}]")
        
        # Skip if already exists
        if drug_name.lower() in existing:
            print(f"  [skip] Already exists")
            skipped.append(drug_name)
            continue
        
        # Search for drug
        setid = search_drug(search_term)
        if not setid:
            failed.append(drug_name)
            continue
        
        # Download PDF
        if download_pdf(setid, drug_name):
            success += 1
        else:
            failed.append(drug_name)
        
        # Be nice to the server
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"[OK] Downloaded: {success}")
    print(f"[--] Skipped (existing): {len(skipped)}")
    print(f"[X]  Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed drugs (download manually from DailyMed):")
        for drug in failed:
            print(f"  - {drug}")
    
    print("\n" + "-" * 60)
    print("Next step: Run 'python run_ingestion.py' to process the new PDFs")
    print("-" * 60 + "\n")


if __name__ == "__main__":
    main()

