"""
Node 3 — Comparative Scoring

Scores ALL candidates in the pool against each other in a single LLM call,
producing a calibrated comparative ranking.

Scoring:
    The LLM produces one overall_score (0–10) per candidate, reflecting their
    fit relative to the rest of the pool and the job description.
    combined_score = overall_score / 10  (stored in Application table, 0–1 scale)

    Cosine similarity from ChromaDB is used ONLY in Node 1 as a retrieval
    filter (top-K selection). It plays no role in the final score.

Environment variables:
    GROQ_API_KEY — required (read by UnifiedLLM / llm_config)
"""

import sys
import json
import asyncio
import logging
from pathlib import Path

import json_repair

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.llm_config import llm_generic
from ..state import BatchScreeningState, ScoredCandidate

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior technical recruiter performing comparative candidate evaluation.

Given a job description and a candidate pool (structured CV data), score ALL candidates
COMPARATIVELY — not in isolation — so scores reflect relative standing within this pool.

Scoring scale:
  8–10 = exceptional match
  5–7  = good match, minor gaps
  3–4  = partial match, notable gaps
  0–2  = poor match

Return ONLY a valid JSON array (no markdown, no commentary) where each element
matches a candidate in the SAME ORDER they were provided:
[
  {
    "source": "<original CV filename>",
    "overall_score": <float 0-10>,
    "justification": "<2-3 sentences covering overall fit, key strengths, and any concerns>",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "key_concerns": ["concern1", "concern2"],
    "recommended_action": "advance" | "reject" | "needs_review"
  }
]

Decision thresholds (your comparative judgment overrides these):
  overall_score >= 6.5 → "advance"
  overall_score 4.5–6.4 → "needs_review"
  overall_score < 4.5 → "reject"

Scoring guidelines:
- Consider the full candidate profile: skills, experience, education, roles, certifications
- Score relative to the pool — the best candidate in a strong pool may score 8-9,
  while the same candidate in a weaker pool might score 9-10
- Be concise but specific in the justification"""


def _clean_json_response(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        clean = inner.strip()
    return clean


def _parse_json_robust(raw: str) -> list[dict]:
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
    Node 3: Score all candidates comparatively via a single LLM call.

    Reads:
        state.job_description    — from Node 1
        state.extracted_cv_data  — full pool from Node 2 (Bucket A + B)

    Writes:
        state.comparative_scores — list of ScoredCandidate sorted by
                                   combined_score descending

    Sets state.error on:
        - Missing inputs
        - LLM API failure
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

    # ── Serialise candidate pool for the prompt ───────────────────────────────
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

    # ── Single LLM call ───────────────────────────────────────────────────────
    try:
        full_prompt = f"SYSTEM:\n{_SYSTEM_PROMPT}\n\nUSER:\n{prompt}"
        result = await asyncio.to_thread(llm_generic.generate, full_prompt)
        raw = result["results"][0]["generated_text"]
        scores_data: list[dict] = _parse_json_robust(raw)

    except (json.JSONDecodeError, ValueError) as exc:
        state.error = f"[Node 3] JSON parse failed on LLM response: {exc}"
        logger.error(state.error)
        return state
    except Exception as exc:
        state.error = f"[Node 3] LLM scoring call failed: {exc}"
        logger.error(state.error)
        return state

    if not scores_data:
        state.error = "[Node 3] LLM returned empty response — no candidates scored"
        logger.error(state.error)
        return state

    # ── Reconcile LLM output to canonical source list ─────────────────────────
    # Two-pass matching:
    #   1. Exact source string match
    #   2. Positional fallback (LLM may garble filenames)
    canonical_sources = [cv.source for cv in state.extracted_cv_data]

    llm_by_source: dict[str, dict] = {
        item.get("source", ""): item
        for item in scores_data
        if item.get("source")
    }
    llm_by_position: list[dict] = list(scores_data)

    if len(scores_data) != len(canonical_sources):
        logger.warning(
            f"[Node 3] LLM returned {len(scores_data)} items but "
            f"expected {len(canonical_sources)} — will match what we can."
        )

    # ── Build ScoredCandidate list ────────────────────────────────────────────
    scored: list[ScoredCandidate] = []
    for i, cv in enumerate(state.extracted_cv_data):
        item = llm_by_source.get(cv.source)

        if item is None and i < len(llm_by_position):
            fallback = llm_by_position[i]
            logger.warning(
                f"[Node 3] Source mismatch: canonical='{cv.source}' not in LLM response — "
                f"positional fallback used (LLM had '{fallback.get('source', '')}' at index {i})"
            )
            item = fallback

        if item is None:
            logger.warning(
                f"[Node 3] No score found for '{cv.source}' (index {i}) — skipping."
            )
            continue

        llm_score = float(item.get("overall_score", 0.0))
        combined  = round(llm_score / 10.0, 4)

        scored.append(
            ScoredCandidate(
                source=cv.source,
                llm_score=llm_score,
                combined_score=combined,
                justification=item.get("justification", ""),
                key_strengths=item.get("key_strengths", []),
                key_concerns=item.get("key_concerns", []),
                recommended_action=item.get("recommended_action", "needs_review"),
            )
        )

    scored.sort(key=lambda s: s.combined_score, reverse=True)
    state.comparative_scores = scored

    if scored:
        logger.info(
            f"[Node 3] Scoring complete — {len(scored)}/{len(canonical_sources)} candidates "
            f"scored. Top: source='{scored[0].source}', score={scored[0].combined_score:.4f}"
        )
    else:
        logger.warning("[Node 3] Scoring returned an empty list — no candidates could be matched.")

    return state