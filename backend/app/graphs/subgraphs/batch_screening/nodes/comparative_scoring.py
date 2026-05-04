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

Given a job description and a pool of candidate profiles (structured CV data), your task
is to score ALL candidates COMPARATIVELY — meaning scores must reflect each candidate's
standing RELATIVE TO THE REST OF THE POOL and the job requirements.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON array (no markdown, no commentary) in the SAME ORDER
candidates were provided:
[
  {
    "source": "<original CV filename>",
    "overall_score": <float 0-10>,
    "justification": "<see requirements below>"
  }
]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORING SCALE (comparative, not absolute)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  8–10  Strongest candidates in the pool — clear match to the role's must-haves,
        demonstrably ahead of peers on key dimensions
  5–7   Competitive but with meaningful gaps versus higher-ranked candidates;
        meets most requirements
  3–4   Partial match; noticeable gaps on core requirements compared to the pool
  0–2   Poor fit relative to the pool; missing critical requirements

Calibration rule: scores must spread across the pool — avoid clustering
everyone at the same band. If the pool is uniformly strong, use the top
of each band; if uniformly weak, use the bottom.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JUSTIFICATION REQUIREMENTS (3–5 sentences per candidate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each justification MUST:
  1. State where this candidate ranks relative to the pool
     (e.g. "Among the top third of this pool…", "Weakest in the pool on…")
  2. Cite 1–2 specific strengths from their profile that support the score
     (e.g. "7 years in data engineering with direct Spark and dbt experience…")
  3. Cite 1–2 specific gaps or concerns relative to what the role needs
     (e.g. "No demonstrated leadership experience, unlike the top candidates…")
  4. Conclude with a concise fit statement that references the job description
     (e.g. "Overall a solid fit for the IC track but behind peers for the
      senior-level scope described in the JD.")

Be specific — reference actual data from the CV (years, tools, titles, companies).
Do NOT use vague phrases like "shows potential" or "decent background".
Do NOT repeat the same justification across candidates."""


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