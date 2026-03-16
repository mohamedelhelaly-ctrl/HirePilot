"""
Node 2 — CV Data Extraction (with re-screening support)

Responsibilities:
1. Query the DB to find which CVs from Node 1's results already have an
   application on this requisition (Bucket A — existing candidates).
2. For Bucket A: reconstruct ExtractedCV from stored ApplicationDetail rows
   so the comparative scorer has their structured data without an LLM call.
3. For Bucket B (new candidates): call the LLM to extract structured CV data,
   then run an email check — if the extracted email matches a candidate already
   in the global candidates table, record the mapping so Node 4 can link the
   new application to the existing candidate row instead of creating a duplicate.
4. Merge Bucket A + Bucket B into state.extracted_cv_data for Node 3.

Bucket routing flag: ExtractedCV.is_existing_candidate
    True  → Bucket A: Node 4 will UPDATE scores/justifications only.
    False → Bucket B: Node 4 will run full candidate get-or-create + insert.

Environment variables:
    GROQ_API_KEY              — required (read by UnifiedLLM / llm_config)
    GROQ_EXTRACTION_SEMAPHORE — optional, default: 5 (max parallel LLM calls)
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

import json_repair

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.llm_config import llm_generic                    # noqa: E402
from db.database import AsyncSessionLocal                   # noqa: E402
from db import crud                                         # noqa: E402
from ..state import BatchScreeningState, ExtractedCV

logger = logging.getLogger(__name__)

MAX_PARALLEL = int(os.getenv("GROQ_EXTRACTION_SEMAPHORE", "5"))
# Truncate CV text to avoid exceeding context window; 6000 chars ≈ ~1500 tokens
CV_TEXT_CHAR_LIMIT = 6000

# ApplicationDetail keys written by Node 4 / _build_application_detail_entries
# Maps detail key → ExtractedCV field name
_DETAIL_KEY_MAP = {
    "technical_skills":       "skills",
    "total_years_experience": "total_years_experience",
    "education":              "education",
    "previous_roles":         "previous_roles",
    "certifications":         "certifications",
    "profile_summary":        "summary",
    "contact_info":           "_contact_info",  # special — unpacked below
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences if the model wrapped the JSON in ```json...```."""
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        clean = inner.strip()
    return clean


def _valid_email(addr: str) -> bool:
    """Minimal email sanity check — must have exactly one @ with non-empty parts."""
    parts = addr.split("@")
    return (
        len(parts) == 2
        and bool(parts[0].strip())
        and bool(parts[1].strip())
        and " " not in addr
    )


# ── LLM extraction prompt ─────────────────────────────────────────────────────

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
Output constraints:
- Keep skills and certifications as arrays of short strings.
- Keep education and previous_roles as arrays of JSON objects in the exact shape shown.
- Use numeric values (not strings) for total_years_experience and previous_roles[].years.
- Do not return markdown or code fences.
If a field cannot be determined, use null for strings and an empty list or 0.0 for floats."""


async def _extract_single(source: str, cv_text: str) -> ExtractedCV:
    """
    LLM extraction for one CV (Bucket B only).
    Returns a minimal ExtractedCV on any failure — pipeline is never blocked
    by a single bad document.
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
            is_existing_candidate=False,
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
        return ExtractedCV(source=source, is_existing_candidate=False, raw_llm_output=str(exc))


def _reconstruct_from_details(
    source: str,
    details: list,
) -> ExtractedCV:
    """
    Reconstruct an ExtractedCV from ApplicationDetail rows (Bucket A).

    detail.key values written by Node 4:
        technical_skills, total_years_experience, education,
        previous_roles, certifications, profile_summary, contact_info
    """
    kwargs: dict = {
        "source": source,
        "is_existing_candidate": True,
    }

    for detail in details:
        key = detail.key
        val = detail.value  # already deserialised JSON (list / dict / scalar)

        if key == "technical_skills":
            kwargs["skills"] = val if isinstance(val, list) else []
        elif key == "total_years_experience":
            kwargs["total_years_experience"] = float(val) if val is not None else 0.0
        elif key == "education":
            kwargs["education"] = val if isinstance(val, list) else []
        elif key == "previous_roles":
            kwargs["previous_roles"] = val if isinstance(val, list) else []
        elif key == "certifications":
            kwargs["certifications"] = val if isinstance(val, list) else []
        elif key == "profile_summary":
            kwargs["summary"] = str(val) if val else ""
        elif key == "contact_info" and isinstance(val, dict):
            kwargs["phone"] = val.get("phone")
            kwargs["linkedin_url"] = val.get("linkedin_url")
            kwargs["email"] = val.get("email") or ""

    return ExtractedCV(**kwargs)


# ── Main node ─────────────────────────────────────────────────────────────────

async def cv_extraction_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 2: Smart extraction — skip LLM for already-screened candidates,
    extract fresh for new ones, then run email dedup on the new cohort.

    Reads:
        state.top_candidates   — list of CandidateDoc from Node 1
        state.requisition_id   — used to query existing applications

    Writes:
        state.extracted_cv_data          — full pool (Bucket A + B) for Node 3
        state.existing_candidate_sources — set of Bucket A source filenames
        state.email_to_candidate_id      — email → candidate.id for Bucket B
                                           where email matched an existing global
                                           candidate

    Does NOT set state.error on individual extraction failures — a minimal
    ExtractedCV is returned per candidate so the pipeline always continues.
    Sets state.error only if top_candidates is empty.
    """
    if state.error:
        return state

    if not state.top_candidates:
        state.error = "[Node 2] No candidates to extract — top_candidates is empty"
        logger.error(state.error)
        return state

    all_sources = [c.source for c in state.top_candidates]

    # ── Step 1: Determine which sources already have applications ─────────────
    # lever_opportunity_id format (set in Node 4): "screening_{req_id}_{source}"
    # We reverse that to recover source filenames for this requisition.
    existing_sources: set[str] = set()
    # application_id lookup for Bucket A: source → app_id (needed for detail fetch)
    source_to_app_id: dict[str, int] = {}

    try:
        async with AsyncSessionLocal() as db:
            applications = await crud.get_applications_by_requisition(
                db, state.requisition_id
            )
            prefix = f"screening_{state.requisition_id}_"
            for app in applications:
                if app.lever_opportunity_id and app.lever_opportunity_id.startswith(prefix):
                    src = app.lever_opportunity_id[len(prefix):]
                    existing_sources.add(src)
                    source_to_app_id[src] = app.id
    except Exception as exc:
        state.error = f"[Node 2] DB query for existing applications failed: {exc}"
        logger.error(state.error)
        return state

    state.existing_candidate_sources = existing_sources

    bucket_a = [c for c in state.top_candidates if c.source in existing_sources]
    bucket_b = [c for c in state.top_candidates if c.source not in existing_sources]

    logger.info(
        f"[Node 2: cv_extraction] requisition_id={state.requisition_id} — "
        f"{len(bucket_a)} existing (Bucket A, skip LLM), "
        f"{len(bucket_b)} new (Bucket B, extract)"
    )

    # ── Step 2: Reconstruct ExtractedCV for Bucket A from ApplicationDetail ───
    bucket_a_results: list[ExtractedCV] = []
    if bucket_a:
        try:
            async with AsyncSessionLocal() as db:
                for cand in bucket_a:
                    app_id = source_to_app_id.get(cand.source)
                    if app_id is None:
                        # Shouldn't happen, but degrade gracefully
                        logger.warning(
                            f"[Node 2] Bucket A: no app_id found for source='{cand.source}' "
                            "— using minimal ExtractedCV"
                        )
                        bucket_a_results.append(
                            ExtractedCV(source=cand.source, is_existing_candidate=True)
                        )
                        continue

                    details = await crud.get_application_details(db, app_id)
                    extracted = _reconstruct_from_details(cand.source, details)
                    bucket_a_results.append(extracted)
                    logger.debug(
                        f"[Node 2] Bucket A: reconstructed '{cand.source}' "
                        f"from {len(details)} detail rows"
                    )
        except Exception as exc:
            # Non-fatal — we still have whatever we reconstructed so far;
            # any missing ones get minimal fallbacks
            logger.warning(f"[Node 2] Bucket A reconstruction partial failure: {exc}")

    # ── Step 3: LLM extraction for Bucket B (new candidates) ─────────────────
    bucket_b_results: list[ExtractedCV] = []
    if bucket_b:
        semaphore = asyncio.Semaphore(MAX_PARALLEL)

        async def _throttled(cand):
            async with semaphore:
                return await _extract_single(cand.source, cand.cv_text)

        raw_results = await asyncio.gather(*[_throttled(c) for c in bucket_b])
        bucket_b_results = list(raw_results)

        successful = sum(1 for r in bucket_b_results if r.skills or r.summary)
        logger.info(
            f"[Node 2] Bucket B extraction: {successful}/{len(bucket_b_results)} "
            "extracted successfully (rest returned minimal fallback)"
        )

    # ── Step 4: Email dedup for Bucket B ─────────────────────────────────────
    # For each freshly extracted Bucket B candidate, check their email against
    # the global candidates table.
    #
    # Two sub-cases when a global email match is found:
    #
    #   A) That candidate already has an application on THIS requisition
    #      (they re-uploaded under a different filename).
    #      → Skip entirely — drop from Bucket B, do NOT add to Bucket A.
    #        Their existing application will be picked up by the Bucket A
    #        reconstruction above under their original filename.
    #        We just silently discard the duplicate new filename.
    #
    #   B) That candidate exists globally but NOT on this requisition
    #      (they applied to a different req before).
    #      → Keep in Bucket B for scoring + insertion, but record the
    #        email → candidate.id mapping so Node 4 links the new application
    #        to the existing candidate row instead of creating a duplicate.
    #
    # Fallback for extraction failures (no email extracted):
    #   Check if a candidate with lever_id == source already has an application
    #   on this requisition. If yes → duplicate re-upload, skip.
    email_to_candidate_id: dict[str, int] = {}
    # Sources to drop from bucket_b_results (duplicate re-upload, same person)
    sources_to_skip: set[str] = set()

    if bucket_b_results:
        # Build set of candidate_ids that already have applications on this
        # requisition — used to detect sub-case A (needed for both email path
        # and lever_id fallback path).
        existing_candidate_ids_on_req: set[int] = set()
        # Also build lever_id → candidate_id map for the fallback path
        lever_id_to_candidate_id: dict[str, int] = {}
        try:
            async with AsyncSessionLocal() as db:
                apps_on_req = await crud.get_applications_by_requisition(
                    db, state.requisition_id
                )
                for app in apps_on_req:
                    existing_candidate_ids_on_req.add(app.candidate_id)

                # Load lever_id for each candidate that has an application here
                for app in apps_on_req:
                    cand = await crud.get_candidate_by_id(db, app.candidate_id)
                    if cand and cand.lever_id:
                        lever_id_to_candidate_id[cand.lever_id] = cand.id
        except Exception as exc:
            logger.warning(
                f"[Node 2] Could not load candidate_ids for requisition — "
                f"dedup sub-case A check may be incomplete: {exc}"
            )

        # ── Email-based dedup (candidates with valid extracted email) ─────────
        valid_results = [
            r for r in bucket_b_results
            if r.email and _valid_email(r.email) and "@screening.internal" not in r.email
        ]
        if valid_results:
            try:
                async with AsyncSessionLocal() as db:
                    for extracted in valid_results:
                        existing = await crud.get_candidate_by_email(db, extracted.email)
                        if not existing:
                            continue  # brand new person — nothing to do

                        if existing.id in existing_candidate_ids_on_req:
                            # Sub-case A: same person, different filename, same req
                            sources_to_skip.add(extracted.source)
                            logger.info(
                                f"[Node 2] Duplicate upload detected (email): "
                                f"source='{extracted.source}' email='{extracted.email}' "
                                f"already screened on this requisition as candidate_id="
                                f"{existing.id} — skipping"
                            )
                        else:
                            # Sub-case B: known candidate, new requisition
                            email_to_candidate_id[extracted.email] = existing.id
                            logger.info(
                                f"[Node 2] Global email match: '{extracted.email}' → "
                                f"existing candidate_id={existing.id} "
                                f"(different requisition — will reuse candidate row)"
                            )
            except Exception as exc:
                logger.warning(f"[Node 2] Email dedup check failed: {exc}")

        # ── lever_id fallback dedup (extraction failed, no email available) ───
        # When the LLM extraction fails, the ExtractedCV has no email. We fall
        # back to checking if a candidate whose lever_id matches this source
        # already has an application on this requisition. This catches the case
        # where the same person re-uploads under a different filename AND their
        # extraction fails (e.g. due to rate limiting).
        no_email_results = [
            r for r in bucket_b_results
            if r.source not in sources_to_skip
            and (not r.email or not _valid_email(r.email) or "@screening.internal" in r.email)
        ]
        for extracted in no_email_results:
            matched_candidate_id = lever_id_to_candidate_id.get(extracted.source)
            if matched_candidate_id and matched_candidate_id in existing_candidate_ids_on_req:
                sources_to_skip.add(extracted.source)
                logger.info(
                    f"[Node 2] Duplicate upload detected (lever_id fallback): "
                    f"source='{extracted.source}' matches existing candidate_id="
                    f"{matched_candidate_id} on this requisition — skipping"
                )

    # Drop duplicate re-uploads from Bucket B
    if sources_to_skip:
        before = len(bucket_b_results)
        bucket_b_results = [r for r in bucket_b_results if r.source not in sources_to_skip]
        logger.info(
            f"[Node 2] Dropped {before - len(bucket_b_results)} duplicate re-upload(s) "
            f"from Bucket B: {sources_to_skip}"
        )

    state.existing_candidate_sources = existing_sources
    state.email_to_candidate_id = email_to_candidate_id

    # ── Step 5: Merge both buckets — Bucket A first (stable ordering) ─────────
    # Bucket A (existing) listed before Bucket B (new) so the comparative scorer
    # always sees the full incumbent pool before the newcomers.
    state.extracted_cv_data = bucket_a_results + bucket_b_results

    logger.info(
        f"[Node 2] Pool ready for scoring: "
        f"{len(bucket_a_results)} existing + {len(bucket_b_results)} new = "
        f"{len(state.extracted_cv_data)} total candidates "
        f"({len(sources_to_skip)} duplicate re-upload(s) discarded)"
    )

    return state