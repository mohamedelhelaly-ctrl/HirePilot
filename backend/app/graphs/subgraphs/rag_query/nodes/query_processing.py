"""
Node 1 — Query Processing

Responsibilities:
- Extract structured filters from natural language query (candidate name, skills, experience, scores)
- Clean query for semantic search (remove filter terms)
- Generate embedding vector for ChromaDB similarity search
- Populate state.processed_query

Environment variables:
    EMBEDDING_MODEL_NAME (via embedding_model.py) — optional, default: BAAI/bge-m3
"""

import logging
from typing import Optional, List
import re

from ..state import RAGQueryState, ProcessedQuery, ExtractedFilters
from utils.embedding_model import get_embedding_model

logger = logging.getLogger(__name__)


# ── Filter Extraction Functions ──────────────────────────────────────────────

def extract_candidate_name(query: str) -> Optional[str]:
    """
    Extract explicit candidate name mentions using common patterns.
    
    Examples:
        "Tell me about John Smith" → "John Smith"
        "candidates named Sarah" → "Sarah"
        "profile of Alice Johnson" → "Alice Johnson"
    """
    # Pattern: "named X", "called X", "about X", "profile of X"
    patterns = [
        r"named\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"called\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"about\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"profile\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"(?:^|\s)([A-Z][a-z]+\s+[A-Z][a-z]+)(?:'s|\s+profile|\s+CV)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            return match.group(1).strip()
    
    return None


def extract_technical_filters(query: str) -> List[str]:
    """
    Extract skill/technology keywords from query.
    
    Uses a whitelist of common technical skills. This can be expanded
    or replaced with a more sophisticated skill taxonomy.
    
    Examples:
        "Python developers" → ["Python"]
        "candidates with React and TypeScript" → ["React", "TypeScript"]
    """
    # Common technical skills (expand as needed)
    skill_whitelist = {
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node", "nodejs", "django", "flask", "fastapi", "spring", "docker",
        "kubernetes", "aws", "gcp", "azure", "sql", "postgresql", "mongodb",
        "redis", "git", "ci/cd", "machine learning", "ml", "ai", "data science",
        "golang", "rust", "c++", "c#", ".net", "ruby", "rails", "php", "laravel"
    }
    
    query_lower = query.lower()
    found_skills = []
    
    for skill in skill_whitelist:
        # Match whole word boundaries to avoid partial matches
        if re.search(rf"\b{re.escape(skill)}\b", query_lower):
            found_skills.append(skill.title())
    
    return found_skills


def extract_experience_requirements(query: str) -> tuple[Optional[float], Optional[float]]:
    """
    Parse experience requirements from query.
    
    Examples:
        "5+ years" → (5.0, None)
        "3-5 years experience" → (3.0, 5.0)
        "senior level" → (7.0, None)
        "junior developers" → (0.0, 3.0)
    
    Returns:
        (min_years, max_years) tuple
    """
    query_lower = query.lower()
    
    # Explicit numeric patterns
    # "5+ years", "5 + years", "5 years+"
    match = re.search(r"(\d+)\s*\+\s*years?", query_lower)
    if match:
        return (float(match.group(1)), None)
    
    # "3-5 years", "3 to 5 years"
    match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*years?", query_lower)
    if match:
        return (float(match.group(1)), float(match.group(2)))
    
    # Level-based heuristics
    if re.search(r"\b(senior|lead|principal)\b", query_lower):
        return (7.0, None)
    if re.search(r"\bmid\s*[-\s]*level\b", query_lower):
        return (3.0, 7.0)
    if re.search(r"\b(junior|entry\s*[-\s]*level)\b", query_lower):
        return (0.0, 3.0)
    
    return (None, None)


def extract_score_filters(query: str) -> tuple[Optional[float], Optional[float]]:
    """
    Parse score requirements from query.
    
    Examples:
        "top candidates" → (0.8, None, None)
        "score above 8" → (None, 8.0, None)
        "technical score over 7" → (None, 7.0, None)
    
    Returns:
        (min_combined_score, min_technical_score, min_assessment_score)
    """
    query_lower = query.lower()
    
    min_combined = None
    min_technical = None
    min_assessment = None
    
    # "top candidates" heuristic
    if re.search(r"\b(top|best|highest\s+(?:rated|scored))\s+candidates?\b", query_lower):
        min_combined = 0.8
    
    # "score above/over X"
    match = re.search(r"score\s+(?:above|over|greater than)\s+(\d+(?:\.\d+)?)", query_lower)
    if match:
        min_combined = float(match.group(1))
        # Normalize if on 0-10 scale
        if min_combined > 1.0:
            min_combined = min_combined / 10.0
    
    # "technical score X"
    match = re.search(r"technical\s+score\s+(?:above|over|greater than)\s+(\d+(?:\.\d+)?)", query_lower)
    if match:
        min_technical = float(match.group(1))
    
    # "assessment score X"
    match = re.search(r"assessment\s+score\s+(?:above|over|greater than)\s+(\d+(?:\.\d+)?)", query_lower)
    if match:
        min_assessment = float(match.group(1))
    
    return (min_combined, min_technical, min_assessment)


def clean_query_for_embedding(query: str, extracted_filters: ExtractedFilters) -> str:
    """
    Remove only NON-SEMANTIC filter terms, keep skills/domain terms.
    
    Remove: candidate names, numeric constraints, filter commands
    Keep: skills, role types, seniority, domain terms
    """
    cleaned = query
    
    # Remove candidate name if found
    if extracted_filters.candidate_name:
        cleaned = re.sub(
            rf"\b{re.escape(extracted_filters.candidate_name)}\b",
            "",
            cleaned,
            flags=re.IGNORECASE
        )
    
    # Remove filter command phrases (but NOT the skills themselves!)
    filter_phrases = [
        r"named\s+\w+",
        r"called\s+\w+",
        r"\d+\s*\+\s*years?",  # "5+ years"
        r"\d+\s*(?:-|to)\s*\d+\s*years?",  # "3-5 years"
        r"(?:with|having)\s+(?:\d+\s*\+?\s*years)",  # "with 5+ years"
        r"score\s+(?:above|over|greater than)\s+\d+(?:\.\d+)?",
        r"technical\s+score\s+(?:above|over|greater than)\s+\d+(?:\.\d+)?",
        r"assessment\s+score\s+(?:above|over|greater than)\s+\d+(?:\.\d+)?",
    ]
    
    for phrase in filter_phrases:
        cleaned = re.sub(phrase, " ", cleaned, flags=re.IGNORECASE)
    
    # Clean up: remove filler words but keep semantic content
    filler_words = [r"\bfind\b", r"\bshow\b", r"\bget\b", r"\blist\b", r"\btell me about\b"]
    for filler in filler_words:
        cleaned = re.sub(filler, " ", cleaned, flags=re.IGNORECASE)
    
    # Clean up whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # Fallback to original if everything removed
    if not cleaned or len(cleaned) < 3:
        return query
    
    return cleaned


# ── Main Node Function ────────────────────────────────────────────────────────

async def query_processing_node(state: RAGQueryState) -> RAGQueryState:
    """
    Node 1: Process user query to extract filters and generate embedding.
    
    Reads:
        state.query — user's natural language question
    
    Writes:
        state.processed_query — ProcessedQuery with filters and embedding
    
    Sets state.error on:
        - Empty query
        - Embedding generation failure
    """
    # ── Fail-fast: propagate upstream errors ──────────────────────────────────
    if state.error:
        return state
    
    if not state.query or not state.query.strip():
        state.error = "[Node 1: query_processing] Query is empty"
        logger.error(state.error)
        return state
    
    logger.info(f"[Node 1: query_processing] Processing query: {state.query[:100]}")
    
    try:
        # ── Step 1: Extract structured filters ────────────────────────────────
        candidate_name = extract_candidate_name(state.query)
        skills = extract_technical_filters(state.query)
        min_years, max_years = extract_experience_requirements(state.query)
        min_combined, min_technical, min_assessment = extract_score_filters(state.query)
        
        extracted_filters = ExtractedFilters(
            candidate_name=candidate_name,
            skills=skills,
            min_years_experience=min_years,
            max_years_experience=max_years,
            min_combined_score=min_combined,
            min_technical_score=min_technical,
            min_assessment_score=min_assessment,
        )
        
        logger.info(
            f"[Node 1] Extracted filters: "
            f"name={candidate_name}, skills={skills}, "
            f"exp=[{min_years}-{max_years}], score>={min_combined}"
        )
        
        # ── Step 2: Clean query for semantic search ───────────────────────────
        cleaned_query = clean_query_for_embedding(state.query, extracted_filters)
        logger.info(f"[Node 1] Cleaned query for embedding: '{cleaned_query}'")
        
        # ── Step 3: Generate embedding ─────────────────────────────────────────
        embedding_model = get_embedding_model()
        embedding = embedding_model.encode(cleaned_query).tolist()
        
        logger.info(
            f"[Node 1] Generated embedding: {len(embedding)} dimensions"
        )
        
        # ── Step 4: Populate state ─────────────────────────────────────────────
        state.processed_query = ProcessedQuery(
            original_query=state.query,
            cleaned_query=cleaned_query,
            embedding=embedding,
            extracted_filters=extracted_filters,
        )
        
        logger.info("[Node 1] Query processing complete")
        return state
        
    except Exception as exc:
        state.error = f"[Node 1: query_processing] Failed: {exc}"
        logger.error(state.error, exc_info=True)
        return state
