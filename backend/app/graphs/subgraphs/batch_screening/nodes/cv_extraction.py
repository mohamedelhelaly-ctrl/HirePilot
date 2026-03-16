"""
Node 2 — CV Data Extraction

Responsibilities:
For each of the top-K candidate CVs from Node 1, call the LLM (via UnifiedLLM
defined in app.utils.llm_config) to extract structured data: skills, experience,
education, roles, certifications, summary.

Calls are fired concurrently (asyncio.gather) with a semaphore to stay within
Groq's rate limits. If a single extraction fails, a minimal ExtractedCV is still
returned so the pipeline is not blocked by one bad document.

Environment variables:
    GROQ_API_KEY              — required (read by UnifiedLLM / llm_config)
    GROQ_EXTRACTION_SEMAPHORE — optional, default: 5 (max parallel calls)
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

import json_repair

# Ensure 'backend/app' is on sys.path so absolute imports work regardless of
# how deep this file sits inside the package hierarchy.
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.llm_config import llm_generic  # noqa: E402
from ..state import BatchScreeningState, ExtractedCV

logger = logging.getLogger(__name__)

MAX_PARALLEL = int(os.getenv("GROQ_EXTRACTION_SEMAPHORE", "5"))
# Truncate CV text to avoid exceeding context window; 6000 chars ≈ ~1500 tokens
CV_TEXT_CHAR_LIMIT = 6000

def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences if the model wrapped the JSON in ```json ... ```."""
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        clean = inner.strip()
    return clean


_SYSTEM_PROMPT = """\
You are an expert CV parser. Extract structured information from the CV text provided.
Return ONLY a valid JSON object with EXACTLY these keys — no extra keys, no commentary:
{
  "full_name": "Candidate's full name as it appears on the CV",
  "email": "candidate@example.com",
  "phone": "+1-555-000-0000 or null if not found",
  "linkedin_url": "https://linkedin.com/in/... or null if not found",
  "skills": ["skill1", "skill2"],
  "total_years_experience": <float>,
  "education": [{"degree": "...", "institution": "..."}],
  "previous_roles": [{"title": "...", "company": "...", "years": <float>}],
  "certifications": ["cert1"],
  "summary": "One concise sentence describing the candidate's profile."
}
If a field cannot be determined, use null for strings and an empty list or 0.0 for floats."""


async def _extract_single(
    source: str,
    cv_text: str,
) -> ExtractedCV:
    """
    Call UnifiedLLM (via llm_cv_extraction) to extract structured data from one CV.
    Returns a minimal ExtractedCV on any failure (non-blocking degradation).
    """
    prompt = (
        f"Extract structured information from this CV:\n\n"
        f"---\n{cv_text[:CV_TEXT_CHAR_LIMIT]}\n---"
    )
    try:
        full_prompt = f"SYSTEM:\n{_SYSTEM_PROMPT}\n\nUSER:\n{prompt}"
        result = await asyncio.to_thread(llm_generic.generate, full_prompt)
        raw = result["results"][0]["generated_text"]
        clean = _clean_json_response(raw)
        try:
            data: dict = json.loads(clean)
        except json.JSONDecodeError:
            data = json_repair.loads(clean)

        return ExtractedCV(
            source=source,
            full_name=data.get("full_name") or "",
            email=data.get("email") or "",
            phone=data.get("phone") or None,
            linkedin_url=data.get("linkedin_url") or None,
            skills=data.get("skills", []),
            total_years_experience=float(data.get("total_years_experience", 0.0)),
            education=data.get("education", []),
            previous_roles=data.get("previous_roles", []),
            certifications=data.get("certifications", []),
            summary=data.get("summary", ""),
            raw_llm_output=raw,
        )

    except Exception as exc:
        logger.warning(
            f"[Node 2] Extraction failed for source={source}: {exc}. "
            "Returning minimal ExtractedCV to keep pipeline running."
        )
        return ExtractedCV(source=source, raw_llm_output=str(exc))


async def cv_extraction_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 2: Extract structured CV data via GROQ for all top candidates.

    Reads:
        state.top_candidates   — list of CandidateDoc from Node 1

    Writes:
        state.extracted_cv_data — list of ExtractedCV (same length as top_candidates)

    Does NOT set state.error on individual CV extraction failures —
    a minimal ExtractedCV is returned per candidate so the pipeline continues.
    Sets state.error only if there is nothing to process.
    """
    # ── Fail-fast: propagate upstream errors ──────────────────────────────────
    if state.error:
        return state

    if not state.top_candidates:
        state.error = "[Node 2] No candidates to extract — top_candidates is empty"
        logger.error(state.error)
        return state

    logger.info(
        f"[Node 2: cv_extraction] Extracting CV data for "
        f"{len(state.top_candidates)} candidates "
        f"(model={llm_generic.model_name}, max_parallel={MAX_PARALLEL})"
    )

    semaphore = asyncio.Semaphore(MAX_PARALLEL)

    async def _throttled(cand):
        async with semaphore:
            return await _extract_single(cand.source, cand.cv_text)

    results = await asyncio.gather(*[_throttled(c) for c in state.top_candidates])
    state.extracted_cv_data = list(results)

    successful = sum(1 for r in results if r.skills or r.summary)
    logger.info(
        f"[Node 2] Extraction complete: {successful}/{len(results)} candidates "
        "extracted successfully (rest returned minimal fallback)"
    )

    return state
