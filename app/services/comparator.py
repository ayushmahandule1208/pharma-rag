"""
Drug Comparison Service - Compare two drugs side-by-side.

Leverages existing search_units table with section classification.
"""
import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from openai import OpenAI

from app.db import DocumentStore
from app.core.config import API_KEYS


@dataclass
class DrugProfile:
    """Structured drug information."""
    drug_name: str
    indications: List[str]
    dosing: Dict[str, str]
    side_effects: Dict[str, List[str]]
    warnings: List[str]
    contraindications: List[str]
    

@dataclass 
class ComparisonResult:
    """Comparison between two drugs."""
    drug1: str
    drug2: str
    indications: Dict
    dosing: Dict
    side_effects: Dict
    warnings: Dict
    summary: str
    sources: Dict[str, str]


class DrugComparator:
    """
    Compare drugs using structured section data.
    """
    
    def __init__(self):
        self.db = DocumentStore()
        self.client = OpenAI(api_key=API_KEYS[0]) if API_KEYS else None
    
    def get_available_drugs(self) -> List[str]:
        """Get list of drugs available for comparison."""
        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT drug_name FROM documents ORDER BY drug_name"
            ).fetchall()
            return [row[0] for row in rows]
    
    def get_drug_sections(self, drug_name: str) -> Dict[str, str]:
        """
        Retrieve all sections for a drug, grouped by section_type.
        """
        with self.db._conn() as conn:
            rows = conn.execute("""
                SELECT su.section_type, su.section_title, su.content
                FROM search_units su
                JOIN documents d ON su.doc_id = d.doc_id
                WHERE LOWER(d.drug_name) = LOWER(?)
                ORDER BY su.section_type, su.chunk_index
            """, (drug_name,)).fetchall()
        
        # Group content by section type
        sections = {}
        for row in rows:
            section_type = row[0] or 'general'
            content = row[2]
            if section_type not in sections:
                sections[section_type] = ""
            sections[section_type] += content + "\n"
        
        return sections
    
    def extract_profile(self, drug_name: str, sections: Dict[str, str]) -> DrugProfile:
        """
        Extract structured profile from drug sections.
        Uses LLM if available, otherwise pattern matching.
        """
        if self.client:
            return self._extract_with_llm(drug_name, sections)
        else:
            return self._extract_with_patterns(drug_name, sections)
    
    def _extract_with_llm(self, drug_name: str, sections: Dict[str, str]) -> DrugProfile:
        """Use LLM to extract structured data."""
        # Combine relevant sections
        context = ""
        for stype in ['indication', 'dosing', 'safety', 'adverse_events', 'general']:
            if stype in sections:
                context += f"\n=== {stype.upper()} ===\n{sections[stype][:2000]}\n"
        
        prompt = f"""Extract structured information about {drug_name} from this FDA label text.

{context[:6000]}

Return ONLY valid JSON with this structure:
{{
    "indications": ["list of approved uses"],
    "dosing": {{
        "starting_dose": "...",
        "maintenance_dose": "...",
        "max_dose": "...",
        "frequency": "...",
        "administration": "..."
    }},
    "side_effects": {{
        "common": ["effects occurring >5%"],
        "serious": ["serious adverse events"]
    }},
    "warnings": ["key warnings"],
    "contraindications": ["contraindications"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            data = json.loads(response.choices[0].message.content)
            return DrugProfile(
                drug_name=drug_name,
                indications=data.get("indications", []),
                dosing=data.get("dosing", {}),
                side_effects=data.get("side_effects", {"common": [], "serious": []}),
                warnings=data.get("warnings", []),
                contraindications=data.get("contraindications", [])
            )
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return self._extract_with_patterns(drug_name, sections)
    
    def _extract_with_patterns(self, drug_name: str, sections: Dict[str, str]) -> DrugProfile:
        """Fallback pattern-based extraction."""
        # Simple extraction based on section content
        indications = []
        if 'indication' in sections:
            # Extract sentences mentioning "indicated" or "treatment"
            text = sections['indication']
            sentences = re.split(r'[.!?]', text)
            indications = [s.strip()[:200] for s in sentences if 'indicated' in s.lower() or 'treatment' in s.lower()][:3]
        
        dosing = {}
        if 'dosing' in sections:
            text = sections['dosing']
            # Look for dose patterns
            dose_match = re.search(r'(\d+(?:\.\d+)?\s*mg)', text)
            if dose_match:
                dosing['starting_dose'] = dose_match.group(1)
            freq_match = re.search(r'(daily|weekly|twice daily|once daily)', text, re.I)
            if freq_match:
                dosing['frequency'] = freq_match.group(1)
            admin_match = re.search(r'(oral|subcutaneous|intravenous|injection)', text, re.I)
            if admin_match:
                dosing['administration'] = admin_match.group(1)
        
        side_effects = {"common": [], "serious": []}
        if 'adverse_events' in sections or 'safety' in sections:
            text = sections.get('adverse_events', '') + sections.get('safety', '')
            # Common side effects often listed with percentages
            effects = re.findall(r'([a-zA-Z\s]+)\s*\(?\d+(?:\.\d+)?%\)?', text)
            side_effects['common'] = list(set([e.strip() for e in effects[:10]]))
        
        warnings = []
        if 'safety' in sections:
            text = sections['safety']
            if 'boxed warning' in text.lower() or 'black box' in text.lower():
                warnings.append("Has Boxed Warning")
        
        return DrugProfile(
            drug_name=drug_name,
            indications=indications or [f"{drug_name} - see full prescribing information"],
            dosing=dosing or {"note": "See full prescribing information"},
            side_effects=side_effects,
            warnings=warnings or ["See full prescribing information"],
            contraindications=[]
        )
    
    def compare(self, drug1: str, drug2: str) -> ComparisonResult:
        """
        Main comparison function.
        """
        # Get sections for both drugs
        sections1 = self.get_drug_sections(drug1)
        sections2 = self.get_drug_sections(drug2)
        
        if not sections1:
            raise ValueError(f"Drug '{drug1}' not found in database")
        if not sections2:
            raise ValueError(f"Drug '{drug2}' not found in database")
        
        # Extract profiles
        profile1 = self.extract_profile(drug1, sections1)
        profile2 = self.extract_profile(drug2, sections2)
        
        # Compare indications
        ind1_set = set(profile1.indications)
        ind2_set = set(profile2.indications)
        indications_comparison = {
            "drug1": profile1.indications,
            "drug2": profile2.indications,
            "shared": list(ind1_set & ind2_set),
            "unique_drug1": list(ind1_set - ind2_set),
            "unique_drug2": list(ind2_set - ind1_set),
        }
        
        # Compare dosing
        dosing_comparison = {
            "drug1": profile1.dosing,
            "drug2": profile2.dosing,
        }
        
        # Compare side effects
        se1_common = set(profile1.side_effects.get('common', []))
        se2_common = set(profile2.side_effects.get('common', []))
        side_effects_comparison = {
            "drug1": profile1.side_effects,
            "drug2": profile2.side_effects,
            "shared": list(se1_common & se2_common),
            "unique_drug1": list(se1_common - se2_common),
            "unique_drug2": list(se2_common - se1_common),
        }
        
        # Compare warnings
        warnings_comparison = {
            "drug1": profile1.warnings,
            "drug2": profile2.warnings,
        }
        
        # Generate summary
        summary = self._generate_summary(drug1, drug2, profile1, profile2)
        
        return ComparisonResult(
            drug1=drug1,
            drug2=drug2,
            indications=indications_comparison,
            dosing=dosing_comparison,
            side_effects=side_effects_comparison,
            warnings=warnings_comparison,
            summary=summary,
            sources={
                drug1: "FDA Label",
                drug2: "FDA Label"
            }
        )
    
    def _generate_summary(self, drug1: str, drug2: str, 
                          profile1: DrugProfile, profile2: DrugProfile) -> str:
        """Generate comparison summary."""
        if self.client:
            prompt = f"""Compare these two drugs briefly (3-4 sentences):

{drug1}:
- Indications: {', '.join(profile1.indications[:3])}
- Dosing: {profile1.dosing}
- Common side effects: {', '.join(profile1.side_effects.get('common', [])[:5])}

{drug2}:
- Indications: {', '.join(profile2.indications[:3])}
- Dosing: {profile2.dosing}
- Common side effects: {', '.join(profile2.side_effects.get('common', [])[:5])}

Focus on key clinical differences."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                return response.choices[0].message.content
            except:
                pass
        
        # Fallback summary
        return f"Comparison between {drug1} and {drug2} based on FDA-approved labeling. Review the sections above for detailed differences in indications, dosing, and safety profiles."
    
    def to_dict(self, result: ComparisonResult) -> dict:
        """Convert result to dictionary for API response."""
        return {
            "drug1": result.drug1,
            "drug2": result.drug2,
            "indications": result.indications,
            "dosing": result.dosing,
            "side_effects": result.side_effects,
            "warnings": result.warnings,
            "summary": result.summary,
            "sources": result.sources
        }

