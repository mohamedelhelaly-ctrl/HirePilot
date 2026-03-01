"""
Node 3 — Comparative Scoring

Responsibilities:
Send ALL extracted candidate CVs + the job description to the LLM (via
UnifiedLLM defined in app.utils.llm_config) in ONE call so the model can score
candidates *relative to each other* (not in isolation), producing calibrated,
comparative rankings.

Scoring formula for combined_score (all components normalised to [0, 1]):
    combined = W_COSINE * cosine_sim
             + W_TECHNICAL * (technical_score / 10)
             + W_BEHAVIORAL * (behavioral_score / 10)

    W_COSINE     = 0.40  (semantic CV-JD similarity from ChromaDB)
    W_TECHNICAL  = 0.35  (skill & experience fit scored by LLM)
    W_BEHAVIORAL = 0.25  (soft skills / cultural fit scored by LLM)

Cosine distance from ChromaDB is converted to similarity:
    cosine_sim = max(0, 1 - distance / 2)
    (LangChain Chroma returns L2 or cosine distance; this normalisation works
     for both — giving 1.0 for identical vectors, 0.0 for fully opposite ones.)

Environment variables:
    GROQ_API_KEY    — required (read by UnifiedLLM / llm_config)
"""

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
from ..state import BatchScreeningState, ScoredCandidate

logger = logging.getLogger(__name__)

# Combined score weights — must sum to 1.0
W_COSINE     = 0.40
W_TECHNICAL  = 0.35
W_BEHAVIORAL = 0.25

_SYSTEM_PROMPT = """\
You are a senior technical recruiter performing comparative candidate evaluation.

Given a job description and a candidate pool (structured CV data), score ALL candidates
COMPARATIVELY — not in isolation — so scores reflect relative standing within this pool.

Scoring scale:
  8–10 = exceptional match        5–7 = good match, minor gaps
  3–4  = partial match, notable gaps   0–2 = poor match

Return ONLY a valid JSON array (no markdown, no commentary) where each element
matches a candidate in the SAME ORDER they were provided:
[
  {
    "source": "<original CV filename>",
    "technical_score": <float 0-10>,
    "behavioral_score": <float 0-10>,
    "technical_justification": "<2-3 sentences>",
    "behavioral_justification": "<2-3 sentences>",
    "overall_justification": "<1-2 sentences>",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "key_concerns": ["concern1", "concern2"],
    "recommended_action": "advance" | "reject" | "needs_review"
  }
]

Decision thresholds (as a guide — your comparative judgment overrides these):
  combined >= 0.65: "advance"    combined 0.45–0.64: "needs_review"    combined < 0.45: "reject"
(combined = 0.40*cosine + 0.35*(tech/10) + 0.25*(behav/10))"""


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


def _parse_json_robust(raw: str) -> list[dict]:
    """
    Parse the LLM's JSON response tolerantly.

    Strategy:
      1. Try standard json.loads on the fence-stripped text (fast path).
      2. Fall back to json_repair.loads which fixes trailing commas, single
         quotes, truncated output, and other common LLM JSON quirks.
    """
    clean = _clean_json_response(raw)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    result = json_repair.loads(clean)
    if isinstance(result, dict):
        # Wrap bare object — model returned {} instead of [{}]
        result = [result]
    return result


async def comparative_scoring_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 3: Score all candidates comparatively via a single GROQ call.

    Reads:
        state.job_description    — from Node 1
        state.extracted_cv_data  — from Node 2
        state.top_candidates     — for cosine_score lookup (from Node 1)

    Writes:
        state.comparative_scores — list of ScoredCandidate

    Sets state.error on:
        - Missing inputs
        - GROQ API failure
        - JSON parse failure
    """
    # ── Fail-fast: propagate upstream errors ──────────────────────────────────
    if state.error:
        return state

    if not state.extracted_cv_data:
        state.error = "[Node 3] No extracted CV data — nothing to score"
        logger.error(state.error)
        return state

    if not state.job_description:
        state.error = "[Node 3] job_description is empty — cannot score without JD"
        logger.error(state.error)
        return state

    # ── Build cosine score lookup: source → raw distance ───────────────────────
    cosine_lookup: dict[str, float] = {
        c.source: c.cosine_score for c in state.top_candidates
    }

    # ── Serialise extracted CV data for the prompt ────────────────────────────
    candidates_payload = json.dumps(
        [
            {
                "source":                 cv.source,
                "skills":                 cv.skills,
                "total_years_experience": cv.total_years_experience,
                "education":              cv.education,
                "previous_roles":         cv.previous_roles,
                "certifications":         cv.certifications,
                "summary":                cv.summary,
            }
            for cv in state.extracted_cv_data
        ],
        indent=2,
    )

    prompt = (
        f"JOB DESCRIPTION:\n{state.job_description}\n\n"
        f"CANDIDATE POOL ({len(state.extracted_cv_data)} candidates):\n"
        f"{candidates_payload}"
    )

    logger.info(
        f"[Node 3: comparative_scoring] Scoring {len(state.extracted_cv_data)} candidates "
        f"via UnifiedLLM (model={llm_generic.model_name})"
    )

    # ── Single LLM call for comparative scoring ───────────────────────────────────────────
    try:
        full_prompt = f"SYSTEM:\n{_SYSTEM_PROMPT}\n\nUSER:\n{prompt}"
        result = await asyncio.to_thread(llm_generic.generate, full_prompt)
        raw = result["results"][0]["generated_text"]
        scores_data: list[dict] = _parse_json_robust(raw)

    except (json.JSONDecodeError, ValueError) as exc:
        state.error = f"[Node 3] JSON parse failed on GROQ response: {exc}"
        logger.error(state.error)
        return state
    except Exception as exc:
        state.error = f"[Node 3] GROQ scoring call failed: {exc}"
        logger.error(state.error)
        return state

    # ── Reconcile LLM output to canonical source list ────────────────────────
    # extracted_cv_data is the CANONICAL ordered list — always trust it, never
    # the LLM's returned source strings.  The LLM may garble filenames (strip
    # extension, change case, truncate) or silently reorder candidates.
    #
    # Two-pass matching:
    #   1. Exact string match:  LLM item's "source" == canonical cv.source
    #   2. Positional fallback: LLM item at index i  → canonical cv at index i

    canonical_sources = [cv.source for cv in state.extracted_cv_data]

    # Index 1: source-string → LLM item (for exact match)
    llm_by_source: dict[str, dict] = {}
    for item in scores_data:
        llm_source = item.get("source", "")
        if llm_source:
            llm_by_source[llm_source] = item

    # Index 2: position → LLM item (for positional fallback)
    llm_by_position: list[dict] = list(scores_data)

    if len(scores_data) != len(canonical_sources):
        logger.warning(
            f"[Node 3] LLM returned {len(scores_data)} items but "
            f"expected {len(canonical_sources)} — will match what we can."
        )

    # ── Compute combined_score and build ScoredCandidate list ─────────────────
    # Iterate over canonical_sources so the resulting list order is deterministic
    # and independent of whatever order the LLM chose to return results in.
    scored: list[ScoredCandidate] = []
    for i, cv in enumerate(state.extracted_cv_data):
        # Pass 1 — exact source match
        item = llm_by_source.get(cv.source)

        # Pass 2 — positional fallback when LLM garbled the source string
        if item is None and i < len(llm_by_position):
            fallback = llm_by_position[i]
            logger.warning(
                f"[Node 3] Source mismatch: canonical='{cv.source}' not found in LLM "
                f"response; positional fallback used (LLM had '{fallback.get('source', '')}' "
                f"at index {i})"
            )
            item = fallback

        if item is None:
            logger.warning(
                f"[Node 3] No LLM score found for '{cv.source}' (index {i}) — skipping."
            )
            continue

        tech  = float(item.get("technical_score",  0.0))
        behav = float(item.get("behavioral_score", 0.0))

        # Convert ChromaDB cosine *distance* → similarity in [0, 1]
        # Always look up by cv.source (canonical), never the LLM's source string
        raw_distance = cosine_lookup.get(cv.source, 1.0)
        cosine_sim   = max(0.0, 1.0 - (raw_distance / 2.0))

        combined = (
            W_COSINE     * cosine_sim
            + W_TECHNICAL  * (tech  / 10.0)
            + W_BEHAVIORAL * (behav / 10.0)
        )

        scored.append(
            ScoredCandidate(
                source=cv.source,   # CANONICAL — never use the LLM's source string
                # application_id left as None — Node 4 fills it after DB insertion
                technical_score=tech,
                behavioral_score=behav,
                combined_score=round(combined, 4),
                cosine_similarity_score=round(cosine_sim, 4),
                technical_justification=item.get("technical_justification",  ""),
                behavioral_justification=item.get("behavioral_justification", ""),
                overall_justification=item.get("overall_justification",       ""),
                key_strengths=item.get("key_strengths", []),
                key_concerns=item.get("key_concerns",   []),
                recommended_action=item.get("recommended_action", "needs_review"),
            )
        )

    # Sort by combined_score descending for cleaner DB write and logging
    scored.sort(key=lambda s: s.combined_score, reverse=True)
    state.comparative_scores = scored

    if scored:
        logger.info(
            f"[Node 3] Scoring complete — {len(scored)}/{len(canonical_sources)} candidates "
            f"scored. Top: source='{scored[0].source}', combined={scored[0].combined_score:.4f}"
        )
    else:
        logger.warning("[Node 3] Scoring returned an empty list — no candidates could be matched.")

    return state
