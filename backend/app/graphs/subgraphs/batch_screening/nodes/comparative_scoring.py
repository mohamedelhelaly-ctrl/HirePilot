"""
Node 3 — Comparative Scoring

Responsibilities:
Send ALL extracted candidate CVs + the job description to the LLM (via
UnifiedLLM defined in app.utils.llm_config) in ONE call so the model can score
candidates *relative to each other* (not in isolation), producing calibrated,
comparative rankings.

This node is unaware of the Bucket A / Bucket B split — it receives the full
merged pool from Node 2 (existing + new candidates) and scores everyone
comparatively in a single LLM call.  This is the key re-screening behaviour:
when new CVs enter the pool, ALL candidates are re-ranked together so scores
reflect the current competition, not stale individual assessments.

Scoring formula for combined_score (all components normalised to [0, 1]):
    combined = W_COSINE * cosine_sim
             + W_TECHNICAL * (technical_score / 10)
             + W_BEHAVIORAL * (behavioral_score / 10)

    W_COSINE     = 0.40  (semantic CV-JD similarity from ChromaDB)
    W_TECHNICAL  = 0.35  (skill & experience fit scored by LLM)
    W_BEHAVIORAL = 0.25  (soft skills / cultural fit scored by LLM)

Cosine distance from ChromaDB is converted to similarity:
    cosine_sim = max(0, 1 - distance / 2)

For existing candidates (Bucket A) whose source does not appear in the current
ChromaDB top-K results, the cosine score stored on their Application row is
used as a fallback so they are not unfairly penalised.

Environment variables:
    GROQ_API_KEY    — required (read by UnifiedLLM / llm_config)
"""

import sys
import json
import asyncio
import logging
from pathlib import Path

import json_repair

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.llm_config import llm_generic          # noqa: E402
from db.database import AsyncSessionLocal         # noqa: E402
from db import crud                               # noqa: E402
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
        result = [result]
    return result


async def comparative_scoring_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 3: Score ALL candidates (existing + new) comparatively via a single
    GROQ call.

    Reads:
        state.job_description            — from Node 1
        state.extracted_cv_data          — full pool from Node 2 (Bucket A + B)
        state.top_candidates             — for fresh cosine_score lookup
        state.existing_candidate_sources — Bucket A sources (for cosine fallback)

    Writes:
        state.comparative_scores — list of ScoredCandidate (full pool, sorted
                                   by combined_score descending)

    Sets state.error on:
        - Missing inputs
        - GROQ API failure
        - JSON parse failure
    """
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

    # ── Build cosine score lookup from Node 1 results ─────────────────────────
    # source → raw ChromaDB distance for candidates returned in current top-K
    fresh_cosine_lookup: dict[str, float] = {
        c.source: c.cosine_score for c in state.top_candidates
    }

    # ── Build fallback cosine lookup for Bucket A from DB ────────────────────
    # Existing candidates may not always rank in the exact top-K if the pool
    # has grown. Use their stored cosine_similarity_score (already a similarity,
    # not a distance) as a fallback rather than defaulting to 0.
    db_cosine_fallback: dict[str, float] = {}
    if state.existing_candidate_sources:
        try:
            async with AsyncSessionLocal() as db:
                prefix = f"screening_{state.requisition_id}_"
                apps = await crud.get_applications_by_requisition(db, state.requisition_id)
                for app in apps:
                    if not app.lever_opportunity_id:
                        continue
                    src = app.lever_opportunity_id[len(prefix):] \
                        if app.lever_opportunity_id.startswith(prefix) else None
                    if src and app.cosine_similarity_score is not None:
                        db_cosine_fallback[src] = float(app.cosine_similarity_score)
        except Exception as exc:
            logger.warning(f"[Node 3] Could not load DB cosine fallbacks: {exc}")

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
        f"({len(state.existing_candidate_sources)} existing + "
        f"{len(state.extracted_cv_data) - len(state.existing_candidate_sources)} new) "
        f"via UnifiedLLM (model={llm_generic.model_name})"
    )

    # ── Single LLM call for comparative scoring ───────────────────────────────
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

    # ── Reconcile LLM output to canonical source list ─────────────────────────
    # Two-pass matching:
    #   1. Exact string match  — LLM item's "source" == canonical cv.source
    #   2. Positional fallback — LLM item at index i → canonical cv at index i
    canonical_sources = [cv.source for cv in state.extracted_cv_data]

    llm_by_source: dict[str, dict] = {}
    for item in scores_data:
        llm_source = item.get("source", "")
        if llm_source:
            llm_by_source[llm_source] = item

    llm_by_position: list[dict] = list(scores_data)

    if len(scores_data) != len(canonical_sources):
        logger.warning(
            f"[Node 3] LLM returned {len(scores_data)} items but "
            f"expected {len(canonical_sources)} — will match what we can."
        )

    # ── Compute combined_score and build ScoredCandidate list ─────────────────
    scored: list[ScoredCandidate] = []
    for i, cv in enumerate(state.extracted_cv_data):
        # Pass 1 — exact source match
        item = llm_by_source.get(cv.source)

        # Pass 2 — positional fallback
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

        # Cosine score resolution:
        #   1. Fresh from ChromaDB top-K (convert distance → similarity)
        #   2. Stored similarity from DB (Bucket A fallback — already [0,1])
        #   3. 0.0 as last resort
        if cv.source in fresh_cosine_lookup:
            raw_distance = fresh_cosine_lookup[cv.source]
            cosine_sim = max(0.0, 1.0 - (raw_distance / 2.0))
        elif cv.source in db_cosine_fallback:
            cosine_sim = db_cosine_fallback[cv.source]
            logger.debug(
                f"[Node 3] Using DB cosine fallback for '{cv.source}': {cosine_sim:.4f}"
            )
        else:
            cosine_sim = 0.0
            logger.warning(
                f"[Node 3] No cosine score available for '{cv.source}' — defaulting to 0.0"
            )

        combined = (
            W_COSINE     * cosine_sim
            + W_TECHNICAL  * (tech  / 10.0)
            + W_BEHAVIORAL * (behav / 10.0)
        )

        scored.append(
            ScoredCandidate(
                source=cv.source,
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