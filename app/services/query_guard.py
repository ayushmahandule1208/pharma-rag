"""
Query Guard - Multi-Layer Defense System

Prevents RAG failures on irrelevant queries:
1. Conversational Filter - Detects greetings, chitchat
2. Relevance Checker - Validates pharmaceutical context
3. Confidence Validator - Ensures quality before answering

This solves the "How are you?" problem where RAG returns nonsense.
"""
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Optional

from app.db.document_store import DocumentStore


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class QueryCategory(Enum):
    """Categories of query intent."""
    PHARMACEUTICAL = "pharmaceutical"      # Valid pharma question
    CONVERSATIONAL = "conversational"      # Greeting, chitchat
    GENERAL_QUESTION = "general_question"  # Non-pharma question
    AMBIGUOUS = "ambiguous"                # Unclear, needs clarification
    GIBBERISH = "gibberish"                # Random characters
    TOO_SHORT = "too_short"                # Too short to understand


@dataclass
class GuardResult:
    """Result from query guard evaluation."""
    should_proceed: bool
    category: QueryCategory
    confidence: float
    message: Optional[str] = None
    suggestion: Optional[str] = None


# =============================================================================
# LAYER 1: CONVERSATIONAL FILTER
# =============================================================================

class ConversationalFilter:
    """
    Detect and handle non-pharmaceutical queries gracefully.
    
    Categories:
    - Greetings: "Hello", "Hi", "Hey"
    - Wellbeing: "How are you?", "What's up?"
    - Thanks: "Thank you", "Thanks"
    - Meta questions: "Who are you?", "What can you do?"
    - Test queries: "test", "hello world"
    """
    
    PATTERNS = {
        'greeting': [
            r'^\s*hello\s*$',
            r'^\s*hi\s*$',
            r'^\s*hey\s*$',
            r'^\s*greetings\s*$',
            r'^\s*good\s*(morning|afternoon|evening|day)\s*$',
            r'^\s*yo\s*$',
        ],
        'wellbeing': [
            r'\bhow\s+are\s+you\b',
            r'\bhow\'s\s+it\s+going\b',
            r'\bwhat\'?s\s+up\b',
            r'\bhow\s+do\s+you\s+do\b',
            r'\bhow\s+are\s+things\b',
        ],
        'thanks': [
            r'\bthank\s*(you|u)\b',
            r'^\s*thanks\s*$',
            r'^\s*thx\s*$',
            r'\bappreciate\s+it\b',
        ],
        'meta': [
            r'\bwho\s+are\s+you\b',
            r'\bwhat\s+are\s+you\b',
            r'\bwhat\s+can\s+you\s+do\b',
            r'\bwhat\s+is\s+your\s+name\b',
            r'\bwhat\'?s\s+your\s+name\b',
            r'^\s*help\s*$',
            r'\btell\s+me\s+about\s+yourself\b',
        ],
        'test': [
            r'^\s*test\s*$',
            r'^\s*testing\s*$',
            r'^\s*hello\s+world\s*$',
            r'^\s*ping\s*$',
            r'^\s*check\s*$',
        ],
        'farewell': [
            r'^\s*bye\s*$',
            r'^\s*goodbye\s*$',
            r'^\s*see\s+you\b',
            r'^\s*later\s*$',
        ]
    }
    
    RESPONSES = {
        'greeting': """Hello! I'm PharmaRAG, a regulatory intelligence assistant. I help with FDA drug label information.

**I can help you with:**
• Drug side effects and safety information
• Dosing and administration details
• Approved indications and uses
• Drug mechanism of action

**Try asking:**
• "What are the side effects of Ozempic?"
• "What is Keytruda approved for?"
• "How is metformin dosed?"
""",
        
        'wellbeing': """I'm functioning well and ready to help! I'm PharmaRAG, specialized in pharmaceutical regulatory information.

**What I can do:**
• Search FDA drug labels for specific information
• Explain drug mechanisms, dosing, and safety
• Provide regulatory citations and sources

**Example questions:**
• "What warnings does Ozempic have?"
• "Explain how GLP-1 agonists work"
• "What is the recommended dose for Humira?"
""",
        
        'thanks': """You're welcome! Let me know if you have any other questions about FDA drug labels or pharmaceutical information.

Feel free to ask about:
• Drug safety and side effects
• Approved uses and indications
• Dosing information
• Drug interactions
""",
        
        'meta': """I'm **PharmaRAG**, a pharmaceutical regulatory intelligence system.

**My Capabilities:**
• 📄 Search FDA-approved drug labels
• 💊 Provide drug information with citations
• ⚠️ Highlight safety warnings and contraindications
• 📊 Compare dosing and indications

**My Knowledge:**
I have access to FDA drug labels and can answer questions about approved medications.

**Example Queries:**
• "What is Ozempic approved for?"
• "What are the black box warnings for Keytruda?"
• "How does metformin work?"
""",
        
        'test': """✓ **System Operational**

PharmaRAG is ready to answer pharmaceutical questions.

**Try one of these:**
• "What are the side effects of Ozempic?"
• "What is Keytruda indicated for?"
• "Tell me about diabetes medications"
""",
        
        'farewell': """Goodbye! Feel free to return anytime you have questions about FDA drug labels or pharmaceutical information.
"""
    }
    
    def check(self, query: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if query is conversational.
        
        Returns:
            (is_conversational, category, response)
        """
        query_lower = query.lower().strip()
        
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return True, category, self.RESPONSES[category]
        
        return False, None, None


# =============================================================================
# LAYER 2: RELEVANCE CHECKER
# =============================================================================

class RelevanceChecker:
    """
    Check if query is pharmaceutical/regulatory related.
    
    Uses domain-specific term detection and known drug matching.
    """
    
    # Pharmaceutical domain indicators
    PHARMA_TERMS = {
        # Drug-related
        'drug', 'medication', 'medicine', 'pharmaceutical', 'prescription',
        'tablet', 'capsule', 'injection', 'infusion', 'oral', 'topical',
        'dose', 'dosage', 'dosing', 'mg', 'ml', 'mcg',
        
        # Medical conditions
        'disease', 'condition', 'disorder', 'syndrome', 'treatment',
        'therapy', 'patient', 'clinical', 'trial', 'study',
        
        # Safety terms
        'side effect', 'adverse', 'warning', 'contraindication', 'risk',
        'toxicity', 'interaction', 'pregnancy', 'lactation', 'pediatric',
        
        # Regulatory terms
        'fda', 'approval', 'approved', 'indication', 'label', 'nda', 'anda',
        'ema', 'regulatory', 'prescribing information',
        
        # Drug classes
        'diabetes', 'cancer', 'oncology', 'cardiovascular', 'hypertension',
        'antibiotic', 'antiviral', 'biosimilar', 'biologic', 'generic',
        'glp-1', 'sglt2', 'ace inhibitor', 'statin', 'ssri', 'nsaid',
        
        # Common drug name patterns/suffixes
        'mab', 'nib', 'pril', 'sartan', 'olol', 'pine', 'statin',
        'cillin', 'mycin', 'azole', 'prazole', 'tide', 'glutide',
        
        # Action words
        'approved for', 'used for', 'treats', 'indicated', 'prescribed',
        'taken', 'administered', 'mechanism', 'pharmacology',
    }
    
    # Common non-pharma terms that should trigger rejection
    NON_PHARMA_INDICATORS = {
        'weather', 'sports', 'movie', 'music', 'recipe', 'cook',
        'capital', 'president', 'country', 'city', 'population',
        'math', 'calculate', 'equation', 'plus', 'minus',
        'joke', 'story', 'poem', 'song', 'game',
        'code', 'program', 'python', 'javascript', 'software',
    }
    
    def __init__(self):
        self.db = DocumentStore()
        self._known_drugs = None
    
    @property
    def known_drugs(self) -> set:
        """Lazy-load known drug names from database."""
        if self._known_drugs is None:
            self._known_drugs = self._load_known_drugs()
        return self._known_drugs
    
    def _load_known_drugs(self) -> set:
        """Load all drug names from database."""
        try:
            with self.db._conn() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT LOWER(drug_name) FROM documents"
                ).fetchall()
                drugs = {row[0] for row in rows if row[0]}
                # Add common variations
                expanded = set()
                for drug in drugs:
                    expanded.add(drug)
                    # Add without common suffixes/prefixes
                    if drug.endswith('®'):
                        expanded.add(drug[:-1])
                return expanded
        except Exception:
            return set()
    
    def has_pharma_terms(self, query: str) -> tuple[bool, list[str]]:
        """
        Check if query contains pharmaceutical terminology.
        
        Returns:
            (has_terms, matched_terms)
        """
        query_lower = query.lower()
        matched = []
        
        # Check pharmaceutical terms
        for term in self.PHARMA_TERMS:
            if term in query_lower:
                matched.append(term)
        
        # Check known drug names
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        drug_matches = query_words & self.known_drugs
        matched.extend(list(drug_matches))
        
        return len(matched) > 0, matched
    
    def has_non_pharma_indicators(self, query: str) -> tuple[bool, list[str]]:
        """Check if query contains clear non-pharma indicators."""
        query_lower = query.lower()
        matched = []
        
        for term in self.NON_PHARMA_INDICATORS:
            if term in query_lower:
                matched.append(term)
        
        return len(matched) > 0, matched
    
    def check(self, query: str) -> tuple[bool, float, str]:
        """
        Check query relevance.
        
        Returns:
            (is_relevant, confidence, reason)
        """
        has_pharma, pharma_terms = self.has_pharma_terms(query)
        has_non_pharma, non_pharma_terms = self.has_non_pharma_indicators(query)
        
        # Clear pharmaceutical query
        if has_pharma and not has_non_pharma:
            return True, 0.9, f"Contains pharma terms: {', '.join(pharma_terms[:3])}"
        
        # Mixed - pharma terms win if they're drug names
        if has_pharma and has_non_pharma:
            # Check if any pharma terms are actual drug names
            drug_terms = set(pharma_terms) & self.known_drugs
            if drug_terms:
                return True, 0.7, f"Contains drug names: {', '.join(list(drug_terms)[:3])}"
            return False, 0.4, f"Ambiguous query with non-pharma indicators"
        
        # Non-pharma query
        if has_non_pharma:
            return False, 0.1, f"Contains non-pharma terms: {', '.join(non_pharma_terms[:3])}"
        
        # No clear indicators - might be a vague pharma question
        return True, 0.5, "No clear indicators, allowing query"


# =============================================================================
# LAYER 3: QUALITY VALIDATOR
# =============================================================================

class QualityValidator:
    """
    Validate that retrieved results are high enough quality to answer.
    
    Checks:
    - Minimum similarity threshold
    - Minimum number of relevant chunks
    - Result consistency (same topic)
    """
    
    # Thresholds
    MIN_VECTOR_SCORE = 0.35       # Minimum semantic similarity
    MIN_BM25_SCORE = 1.0          # Minimum BM25 score
    MIN_RELEVANT_CHUNKS = 1       # Need at least this many good chunks
    MAX_DRUG_DIVERSITY = 5        # Too many drugs = ambiguous query
    
    def validate_results(
        self, 
        results: list, 
        query: str
    ) -> tuple[bool, float, str]:
        """
        Validate search results quality.
        
        Args:
            results: List of SearchResult objects
            query: Original query
            
        Returns:
            (is_valid, confidence, reason)
        """
        if not results:
            return False, 0.0, "No results found"
        
        # Check score thresholds
        good_results = []
        for r in results:
            # Check if result has good semantic or keyword score
            vector_ok = getattr(r, 'vector_score', 0) >= self.MIN_VECTOR_SCORE
            bm25_ok = getattr(r, 'bm25_score', 0) >= self.MIN_BM25_SCORE
            rerank_ok = getattr(r, 'rerank_score', 0) > 0  # Any rerank score is good
            
            if vector_ok or bm25_ok or rerank_ok:
                good_results.append(r)
        
        if len(good_results) < self.MIN_RELEVANT_CHUNKS:
            return False, 0.2, f"Only {len(good_results)} results above quality threshold"
        
        # Check drug diversity (too many = ambiguous)
        drugs = set()
        for r in results[:5]:
            drug = getattr(r, 'drug_name', 'Unknown')
            if drug and drug != 'Unknown':
                drugs.add(drug.lower())
        
        if len(drugs) > self.MAX_DRUG_DIVERSITY:
            return False, 0.3, f"Query matches {len(drugs)} different drugs (too ambiguous)"
        
        # Calculate confidence based on top result scores
        top_scores = []
        for r in results[:3]:
            # Prefer rerank score, fall back to vector score
            score = getattr(r, 'rerank_score', 0) or getattr(r, 'vector_score', 0)
            top_scores.append(score)
        
        avg_score = sum(top_scores) / len(top_scores) if top_scores else 0
        
        # Normalize confidence
        if avg_score > 0.6:
            confidence = 0.9
        elif avg_score > 0.4:
            confidence = 0.7
        elif avg_score > 0.3:
            confidence = 0.5
        else:
            confidence = 0.3
        
        return True, confidence, f"Found {len(good_results)} quality results"


# =============================================================================
# MAIN QUERY GUARD
# =============================================================================

class QueryGuard:
    """
    Main query guard that combines all defense layers.
    
    Usage:
        guard = QueryGuard()
        result = guard.evaluate(query)
        
        if not result.should_proceed:
            return result.message  # Return friendly response
        else:
            # Continue with RAG pipeline
    """
    
    def __init__(self):
        self.conversational_filter = ConversationalFilter()
        self.relevance_checker = RelevanceChecker()
        self.quality_validator = QualityValidator()
    
    def evaluate(self, query: str) -> GuardResult:
        """
        Evaluate query through all defense layers.
        
        Returns:
            GuardResult with decision and optional response
        """
        # Pre-processing
        query = query.strip()
        
        # =====================================================
        # CHECK 1: Empty or too short
        # =====================================================
        if len(query) < 2:
            return GuardResult(
                should_proceed=False,
                category=QueryCategory.TOO_SHORT,
                confidence=1.0,
                message="Please provide a more detailed question about pharmaceutical or drug information.",
                suggestion="Try asking: 'What are the side effects of [drug name]?'"
            )
        
        # =====================================================
        # CHECK 2: Gibberish detection
        # =====================================================
        if self._is_gibberish(query):
            return GuardResult(
                should_proceed=False,
                category=QueryCategory.GIBBERISH,
                confidence=0.9,
                message="I couldn't understand that query. Please try rephrasing.",
                suggestion="Example: 'What is Ozempic used for?'"
            )
        
        # =====================================================
        # CHECK 3: Conversational filter
        # =====================================================
        is_conv, category, response = self.conversational_filter.check(query)
        
        if is_conv:
            return GuardResult(
                should_proceed=False,
                category=QueryCategory.CONVERSATIONAL,
                confidence=1.0,
                message=response
            )
        
        # =====================================================
        # CHECK 4: Relevance check
        # =====================================================
        is_relevant, rel_confidence, rel_reason = self.relevance_checker.check(query)
        
        if not is_relevant:
            return GuardResult(
                should_proceed=False,
                category=QueryCategory.GENERAL_QUESTION,
                confidence=rel_confidence,
                message=self._get_non_pharma_response(query),
                suggestion="Try asking about specific drugs, medications, or treatments."
            )
        
        # Low confidence but might be relevant - proceed with caution
        if rel_confidence < 0.5:
            return GuardResult(
                should_proceed=True,
                category=QueryCategory.AMBIGUOUS,
                confidence=rel_confidence,
                message=None,  # Proceed but might need validation later
                suggestion=None
            )
        
        # =====================================================
        # PASSED ALL CHECKS - Proceed with RAG
        # =====================================================
        return GuardResult(
            should_proceed=True,
            category=QueryCategory.PHARMACEUTICAL,
            confidence=rel_confidence,
            message=None
        )
    
    def validate_results(
        self, 
        results: list, 
        query: str, 
        initial_evaluation: GuardResult
    ) -> GuardResult:
        """
        Post-retrieval validation of results quality.
        
        Call this after retrieval to check if results are good enough.
        """
        is_valid, confidence, reason = self.quality_validator.validate_results(results, query)
        
        if not is_valid:
            # Results not good enough
            return GuardResult(
                should_proceed=False,
                category=QueryCategory.AMBIGUOUS,
                confidence=confidence,
                message=self._get_low_quality_response(query, reason),
                suggestion="Try being more specific or including a drug name."
            )
        
        return GuardResult(
            should_proceed=True,
            category=initial_evaluation.category,
            confidence=confidence,
            message=None
        )
    
    def _is_gibberish(self, query: str) -> bool:
        """Detect random/gibberish text."""
        # Too many consonants in a row
        if re.search(r'[bcdfghjklmnpqrstvwxyz]{5,}', query.lower()):
            return True
        
        # Mostly non-alphabetic
        alpha_ratio = sum(c.isalpha() or c.isspace() for c in query) / max(len(query), 1)
        if alpha_ratio < 0.5 and len(query) > 5:
            return True
        
        # Repeated characters
        if re.search(r'(.)\1{4,}', query):
            return True
        
        return False
    
    def _get_non_pharma_response(self, query: str) -> str:
        """Generate response for non-pharmaceutical queries."""
        return f"""I specialize in **pharmaceutical and FDA drug label information**.

Your question doesn't appear to be related to medications or drug regulatory information.

**I can help with:**
• 💊 Drug side effects and safety warnings
• 📋 Approved indications and uses
• 💉 Dosing and administration
• ⚠️ Drug interactions and contraindications
• 📄 FDA regulatory information

**Try asking:**
• "What is Ozempic approved for?"
• "What are the side effects of Keytruda?"
• "How is Humira administered?"
• "What warnings does metformin have?"
"""
    
    def _get_low_quality_response(self, query: str, reason: str) -> str:
        """Generate response when results are low quality."""
        return f"""I found limited information for your query.

**Reason:** {reason}

**Suggestions:**
• Include a specific drug name (e.g., "Ozempic", "Keytruda")
• Ask about specific aspects (side effects, dosing, indications)
• Check the spelling of drug names

**Example queries:**
• "What are the side effects of Ozempic?"
• "What is Keytruda indicated for?"
• "How often is Humira administered?"

If the drug isn't in my database, I may not have information about it.
"""


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_query_guard = None

def get_query_guard() -> QueryGuard:
    """Get or create singleton QueryGuard."""
    global _query_guard
    if _query_guard is None:
        _query_guard = QueryGuard()
    return _query_guard

