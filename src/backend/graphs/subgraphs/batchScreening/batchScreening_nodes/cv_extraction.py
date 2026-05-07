"""
Node 2 — CV Data Extraction (with re-screening support)

Responsibilities:
1. Query the DB to find which CVs from Node 1's results already have an
   application on this requisition (Bucket A — existing candidates).

2. For Bucket A: reconstruct ExtractedCV from stored ApplicationDetail rows
   so the comparative scorer has their structured data without an LLM call.

3. For Bucket B (new candidates): call the LLM to extract structured CV data,
   then calculate total_years_experience using the ExperienceCalculator (Python,
   not the LLM). 
   Run email dedup to detect duplicate uploads and link returning
   candidates to their existing global Candidate row.

4. Merge Bucket A + Bucket B into state.extracted_cv_data for Node 3.

Experience calculation approach:
    The LLM extracts roles with start_date, end_date, and employment type.
    Python (ExperienceCalculator) filters out internships / part-time / volunteer
    roles, merges overlapping periods, and calculates the accurate total.
    total_years_experience is NEVER trusted from the LLM directly.

Role schema expected from LLM:
    {
      "title":      "Job Title",
      "company":    "Company Name",
      "start_date": "3/2024",   ← MM/YYYY or "Present"
      "end_date":   "Present",  ← MM/YYYY or "Present"
      "type":       "full_time" ← full_time | part_time | internship |
                                  freelance | volunteer | trainer | instructor
    }

Bucket routing flag: ExtractedCV.is_existing_candidate
    True  → Bucket A: Node 4 will UPDATE scores only.
    False → Bucket B: Node 4 will run full candidate get-or-create + insert.

"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

import json_repair

from stores.llm.llm_config import llm_generic
from stores.llm.experience_calculator import calculate_experience
from models.database import AsyncSessionLocal
from ..batchScreening_state import BatchScreeningState, ExtractedCV
from controllers.ApplicationController import ApplicationController
from controllers.CandidateController import CandidateController
application_controller = ApplicationController()
candidate_controller = CandidateController()

logger = logging.getLogger(__name__)

MAX_PARALLEL    = int(os.getenv("MAX_PARALLEL", "5"))
CV_TEXT_CHAR_LIMIT = 6000  # ~1500 tokens — keeps us inside context window


# Helpers

def _clean_json_response(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        clean = inner.strip()
    return clean


def _valid_email(addr: str) -> bool:
    parts = addr.split("@")
    return (
        len(parts) == 2
        and bool(parts[0].strip())
        and bool(parts[1].strip())
        and " " not in addr
    )


# LLM extraction prompts

# Prompt 1: general CV info — no roles/dates so the model isn't juggling nested date logic at the same time as identity fields.

_SYSTEM_PROMPT_MAIN = """\
You are an expert CV parser. Extract structured information from the CV text provided.
Return ONLY a valid JSON object with EXACTLY these keys — no extra keys, no commentary:
{
  "full_name": "Candidate's full name as it appears on the CV",
  "email": "candidate@example.com or null",
  "phone": "+1-555-000-0000 or null",
  "linkedin_url": "https://linkedin.com/in/... or null",
  "skills": ["skill1", "skill2"],
  "education": [{"degree": "...", "institution": "..."}],
  "certifications": ["cert1", "cert2"],
  "summary": "One concise sentence describing the candidate's profile."
}

Output constraints:
- skills and certifications: arrays of short strings — NEVER objects or dicts.
- education: array of {degree, institution} objects.
- Use an empty array [] if no items exist for a list field — NEVER null for arrays.
- Do not return markdown or code fences.
- Use null only for scalar string fields that cannot be determined."""

# Prompt 2: roles only — small, focused output so the model concentrates entirely on extracting dates correctly.
_SYSTEM_PROMPT_ROLES = """\
You are a CV parser. Extract ONLY the list of previous jobs and roles from the CV text.
Return ONLY a valid JSON array — no other text, no code fences, no explanation.
Each element must have EXACTLY these five keys:
[
  {
    "title": "Job title",
    "company": "Company name",
    "start_date": "MM/YYYY",
    "end_date": "MM/YYYY or Present",
    "type": "full_time"
  }
]

STRICT date rules — follow exactly:
- start_date and end_date MUST be in MM/YYYY format: "3/2024", "11/2022", "07/2019".
- If only a year is given, use "1/YYYY" for start_date and "12/YYYY" for end_date.
- If the role is current/ongoing, use exactly the word "Present" for end_date.
- NEVER put a job title, company name, or any non-date text into a date field.
- NEVER use null for dates — use "Present" if the role appears to be ongoing.

STRICT type rules:
- Use one of: full_time, part_time, internship, freelance, volunteer, trainer, instructor.
- Default to "full_time" if the employment type is not explicitly stated.

Extract ALL roles — do not skip internships or part-time work.
Return an empty array [] if no roles are found."""


async def _extract_single(source: str, cv_text: str) -> ExtractedCV:
    """
    Two-prompt parallel extraction for one CV (Bucket B).

    Prompt 1 (_SYSTEM_PROMPT_MAIN)  — general CV fields (identity, skills,
        education, certifications, summary).  Simpler output = fewer hallucinations.
    Prompt 2 (_SYSTEM_PROMPT_ROLES) — roles/dates only, with strict date rules.
        Isolated so the model focuses entirely on MM/YYYY formatting.

    Both calls run concurrently via asyncio.gather.  Python calculates
    total_years_experience from the roles list; it is never trusted from the LLM.

    Returns a minimal ExtractedCV on any failure so the pipeline is never
    blocked by a single bad document.
    """
    truncated = cv_text[:CV_TEXT_CHAR_LIMIT]

    main_full  = (
        f"SYSTEM:\n{_SYSTEM_PROMPT_MAIN}\n\nUSER:\n"
        f"Extract structured information from this CV:\n\n---\n{truncated}\n---"
    )
    roles_full = (
        f"SYSTEM:\n{_SYSTEM_PROMPT_ROLES}\n\nUSER:\n"
        f"Extract all previous jobs and roles from this CV:\n\n---\n{truncated}\n---"
    )

    try:
        main_result, roles_result = await asyncio.gather(
            asyncio.to_thread(llm_generic.generate, main_full),
            asyncio.to_thread(llm_generic.generate, roles_full),
        )

        raw_main  = main_result["results"][0]["generated_text"]
        raw_roles = roles_result["results"][0]["generated_text"]

        def _parse(raw: str, expected: type):
            clean = _clean_json_response(raw)
            try:
                parsed = json.loads(clean)
            except json.JSONDecodeError:
                repaired = json_repair.loads(clean)
                if not isinstance(repaired, expected):
                    raise ValueError(
                        f"json_repair returned {type(repaired).__name__}, "
                        f"expected {expected.__name__}"
                    )
                return repaired
            if not isinstance(parsed, expected):
                raise ValueError(
                    f"Parsed JSON is {type(parsed).__name__}, "
                    f"expected {expected.__name__}"
                )
            return parsed

        data: dict      = _parse(raw_main, dict)
        roles_list: list = _parse(raw_roles, list)

        roles = [r for r in roles_list if isinstance(r, dict)]

        total_years = calculate_experience(roles)
        logger.debug(
            f"[Node 2] Experience calculated for '{source}': "
            f"{total_years} years from {len(roles)} extracted roles"
        )

        return ExtractedCV(
            source=source,
            is_existing_candidate=False,
            full_name=data.get("full_name") or "",
            email=data.get("email") or "",
            phone=data.get("phone") or None,
            linkedin_url=data.get("linkedin_url") or None,
            skills=data.get("skills") or [],
            total_years_experience=total_years,
            education=data.get("education") or [],
            previous_roles=roles,
            certifications=[
                str(c.get("name") or c.get("title") or next(iter(c.values()), ""))
                if isinstance(c, dict) else str(c)
                for c in (data.get("certifications") or [])
                if c
            ],
            summary=data.get("summary") or "",
            raw_llm_output=f"[main]\n{raw_main}\n\n[roles]\n{raw_roles}",
        )

    except Exception as exc:
        logger.warning(
            f"[Node 2] Extraction failed for source='{source}': {exc}. "
            "Returning minimal ExtractedCV to keep pipeline running."
        )
        return ExtractedCV(source=source, is_existing_candidate=False, raw_llm_output=str(exc))


def _reconstruct_from_details(source: str, details: list) -> ExtractedCV:
    """
    Reconstruct an ExtractedCV from ApplicationDetail rows (Bucket A).

    ApplicationDetail keys written by Node 4:
        technical_skills, total_years_experience, education,
        previous_roles, certifications, profile_summary, contact_info

    For Bucket A candidates the total_years_experience stored in the DB was
    already calculated by Python on their first screening run, so we trust it
    directly here — no recalculation needed.
    """
    kwargs: dict = {"source": source, "is_existing_candidate": True}

    for detail in details:
        key = detail.key
        val = detail.value  # already deserialised JSON

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
            kwargs["phone"]        = val.get("phone")
            kwargs["linkedin_url"] = val.get("linkedin_url")
            kwargs["email"]        = val.get("email") or ""

    return ExtractedCV(**kwargs)


# ── Main node ─────────────────────────────────────────────────────────────────

async def cv_extraction_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 2: Smart extraction with Python-calculated experience.

    Reads:
        state.top_candidates   — list of CandidateDoc from Node 1
        state.requisition_id   — used to query existing applications

    Writes:
        state.extracted_cv_data          — full pool (Bucket A + B) for Node 3
        state.existing_candidate_sources — set of Bucket A source filenames
        state.email_to_candidate_id      — email → candidate.id for Bucket B
                                           global matches
    """
    if state.error:
        return state

    if not state.top_candidates:
        state.error = "[Node 2] No candidates to extract — top_candidates is empty"
        logger.error(state.error)
        return state

    # ── Step 1: Determine Bucket A (already have an application here) ─────────
    existing_sources: set[str] = set()
    source_to_app_id: dict[str, int] = {}

    try:
        async with AsyncSessionLocal() as db:
            applications = await application_controller.get_applications_by_requisition(state.requisition_id, db)
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

    # ── Step 2: Reconstruct Bucket A from ApplicationDetail rows ─────────────
    bucket_a_results: list[ExtractedCV] = []
    if bucket_a:
        try:
            async with AsyncSessionLocal() as db:
                for cand in bucket_a:
                    app_id = source_to_app_id.get(cand.source)
                    if app_id is None:
                        logger.warning(
                            f"[Node 2] Bucket A: no app_id for source='{cand.source}' "
                            "— using minimal ExtractedCV"
                        )
                        bucket_a_results.append(
                            ExtractedCV(source=cand.source, is_existing_candidate=True)
                        )
                        continue

                    
                    details = await application_controller.get_application_details(db, app_id)
                    extracted = _reconstruct_from_details(cand.source, details)
                    bucket_a_results.append(extracted)
                    logger.debug(
                        f"[Node 2] Bucket A: reconstructed '{cand.source}' "
                        f"from {len(details)} detail rows"
                    )
        except Exception as exc:
            logger.warning(f"[Node 2] Bucket A reconstruction partial failure: {exc}")

    # Step 3: LLM extraction for Bucket B
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
    email_to_candidate_id: dict[str, int] = {}
    sources_to_skip: set[str] = set()

    if bucket_b_results:
        existing_candidate_ids_on_req: set[int] = set()
        lever_id_to_candidate_id: dict[str, int] = {}
        try:
            async with AsyncSessionLocal() as db:
                apps_on_req = await application_controller.get_applications_by_requisition(db, state.requisition_id)
                for app in apps_on_req:
                    existing_candidate_ids_on_req.add(app.candidate_id)
                for app in apps_on_req:
                    cand = await candidate_controller.get_candidate(app.candidate_id, db)
                    if cand and cand.lever_id:
                        lever_id_to_candidate_id[cand.lever_id] = cand.id
        except Exception as exc:
            logger.warning(
                f"[Node 2] Could not load candidate_ids for requisition — "
                f"dedup check may be incomplete: {exc}"
            )

        # Email-based dedup
        valid_results = [
            r for r in bucket_b_results
            if r.email and _valid_email(r.email) and "@screening.internal" not in r.email
        ]
        if valid_results:
            try:
                async with AsyncSessionLocal() as db:
                    for extracted in valid_results:
                        existing = await candidate_controller.get_candidate_by_email(db, extracted.email)
                        if not existing:
                            continue

                        if existing.id in existing_candidate_ids_on_req:
                            # Same person, different filename, same req → drop
                            sources_to_skip.add(extracted.source)
                            logger.info(
                                f"[Node 2] Duplicate upload detected (email): "
                                f"source='{extracted.source}' email='{extracted.email}' "
                                f"already screened as candidate_id={existing.id} — skipping"
                            )
                        else:
                            # Known globally, new req → reuse candidate row
                            email_to_candidate_id[extracted.email] = existing.id
                            logger.info(
                                f"[Node 2] Global email match: '{extracted.email}' → "
                                f"candidate_id={existing.id} (different requisition)"
                            )
            except Exception as exc:
                logger.warning(f"[Node 2] Email dedup check failed: {exc}")

        # lever_id fallback for candidates with no extractable email
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
                    f"source='{extracted.source}' → candidate_id={matched_candidate_id} — skipping"
                )

    # Drop duplicate re-uploads
    if sources_to_skip:
        before = len(bucket_b_results)
        bucket_b_results = [r for r in bucket_b_results if r.source not in sources_to_skip]
        logger.info(
            f"[Node 2] Dropped {before - len(bucket_b_results)} duplicate re-upload(s): "
            f"{sources_to_skip}"
        )

    state.email_to_candidate_id = email_to_candidate_id

    # ── Step 5: Merge buckets — Bucket A first ────────────────────────────────
    state.extracted_cv_data = bucket_a_results + bucket_b_results

    logger.info(
        f"[Node 2] Pool ready for scoring: "
        f"{len(bucket_a_results)} existing + {len(bucket_b_results)} new = "
        f"{len(state.extracted_cv_data)} total candidates "
        f"({len(sources_to_skip)} duplicate(s) discarded)"
    )

    return state