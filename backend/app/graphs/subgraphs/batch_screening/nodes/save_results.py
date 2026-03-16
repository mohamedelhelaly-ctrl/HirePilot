"""
Node 4 — Save Results to PostgreSQL

Responsibilities:
For every scored candidate, create DB records and persist results across
four tables:

1. Candidate table  (get-or-create)
   - full_name derived from CV filename stem
   - email placeholder: {filename_stem}@screening.internal
   - lever_id = source filename (unique stable identifier)

2. Application table  (create)
   - links candidate → requisition
   - lever_opportunity_id = "screening_{requisition_id}_{source}"
   - cosine_similarity_score, technical_score, behavioral_score, combined_score
   - status transition: SCREENING_PASSED / SCREENING_REJECTED / unchanged

3. ScreeningResult table (UPSERT)
   - scores, justifications, key_strengths, key_concerns, recommended_action

4. ApplicationDetail table (replace)
   - DELETE then INSERT one row per extracted skill

Environment variables:
    DATABASE_URL (via database.py environment variables) — required
"""

import sys
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

# Ensure 'backend/app' is on sys.path so absolute imports work regardless of
# how deep this file sits inside the package hierarchy.
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import delete

from db.database import AsyncSessionLocal            # noqa: E402
from db.models import ApplicationDetail, ApplicationStatus  # noqa: E402
from db import crud                                  # noqa: E402
from schemas import (
    CandidateCreate,
    ApplicationCreate,
    ScreeningResultCreate,
    ScreeningResultUpdate,
    ApplicationDetailCreate,
)
from ..state import BatchScreeningState, ExtractedCV  # noqa: E402

logger = logging.getLogger(__name__)


async def save_results_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 4: Persist all screening results to PostgreSQL.

    Reads:
        state.comparative_scores  — list of ScoredCandidate from Node 3
        state.extracted_cv_data   — list of ExtractedCV from Node 2

    Writes:
        state.saved_count — number of applications successfully persisted

    Sets state.error on:
        - Empty comparative_scores
        - DB transaction failure (rolls back on error)
    """
    # ── Fail-fast: propagate upstream errors ──────────────────────────────────
    if state.error:
        return state

    if not state.comparative_scores:
        state.error = "[Node 4] No scores to save — comparative_scores is empty"
        logger.error(state.error)
        return state

    logger.info(
        f"[Node 4: save_results] Persisting results for "
        f"{len(state.comparative_scores)} candidates to PostgreSQL"
    )

    # Build lookup: source → ExtractedCV (from Node 2)
    cv_lookup: dict[str, ExtractedCV] = {
        cv.source: cv for cv in state.extracted_cv_data
    }

    now = datetime.now(timezone.utc)
    saved = 0

    async with AsyncSessionLocal() as db:
        for scored in state.comparative_scores:
            source = scored.source
            try:
                # ── 1. Get-or-create Candidate ─────────────────────────────────────
                extracted = cv_lookup.get(source)
                if extracted is None:
                    logger.warning(
                        f"[Node 4] No ExtractedCV found for source='{source}' — "
                        "identity fields and skills will use fallback values. "
                        "This indicates a source-string mismatch upstream (Node 3)."
                    )

                # Use real extracted identity; fall back to filename stem only if
                # the LLM could not find a name or email in the CV.
                filename_stem = Path(source).stem
                full_name = (
                    extracted.full_name
                    if extracted and extracted.full_name
                    else filename_stem.replace("_", " ").replace("-", " ").title()
                )
                # Sanitize: replace any whitespace/non-alphanumeric chars with
                # hyphens so the local-part of the fallback email is always valid.
                safe_stem = re.sub(r"[^a-z0-9]+", "-", filename_stem.lower()).strip("-")
                extracted_email = extracted.email if extracted else ""
                # Validate the extracted email minimally (must contain exactly one @
                # with non-empty local part and domain) before trusting it.
                def _valid_email(addr: str) -> bool:
                    parts = addr.split("@")
                    return (len(parts) == 2
                            and bool(parts[0].strip())
                            and bool(parts[1].strip())
                            and " " not in addr)
                email = (
                    extracted_email
                    if _valid_email(extracted_email)
                    else f"{safe_stem}@screening.internal"
                )
                candidate = await crud.get_or_create_candidate(
                    db,
                    CandidateCreate(
                        full_name=full_name,
                        email=email,
                        phone=extracted.phone if extracted else None,
                        linkedin_url=extracted.linkedin_url if extracted else None,
                        lever_id=source,   # stable unique key — source filename
                    ),
                )

                # ── 2. Create Application ────────────────────────────────────────
                lever_opp_id = f"screening_{state.requisition_id}_{source}"
                # Re-use existing application if this candidate was screened before
                application = await crud.get_application_by_lever_opportunity_id(
                    db, lever_opp_id
                )
                if not application:
                    application = await crud.create_application(
                        db,
                        ApplicationCreate(
                            candidate_id=candidate.id,
                            requisition_id=state.requisition_id,
                            lever_opportunity_id=lever_opp_id,
                        ),
                    )

                app_id = application.id
                # Backfill application_id on the scored object for audit/result reporting
                scored.application_id = app_id

                # ── 3. Update Application scores ───────────────────────────────
                application.cosine_similarity_score = scored.cosine_similarity_score
                application.technical_score         = scored.technical_score
                application.behavioral_score        = scored.behavioral_score
                application.combined_score          = scored.combined_score
                application.last_activity_at        = now
                await db.commit()

                # ── 4. Transition status ─────────────────────────────────────────
                if scored.recommended_action == "advance":
                    await crud.update_application_status(
                        db, app_id, ApplicationStatus.SCREENING_PASSED
                    )
                elif scored.recommended_action == "reject":
                    await crud.update_application_status(
                        db, app_id, ApplicationStatus.SCREENING_REJECTED
                    )
                # "needs_review" → leave current status unchanged

                # ── 5. Upsert ScreeningResult ──────────────────────────────────
                sr_payload = dict(
                    technical_score=scored.technical_score,
                    behavioral_score=scored.behavioral_score,
                    technical_justification=scored.technical_justification,
                    behavioral_justification=scored.behavioral_justification,
                    overall_justification=scored.overall_justification,
                    key_strengths=scored.key_strengths,
                    key_concerns=scored.key_concerns,
                    recommended_action=scored.recommended_action,
                )
                existing_sr = await crud.get_screening_result_by_application(db, app_id)
                if existing_sr:
                    await crud.update_screening_result(
                        db, app_id, ScreeningResultUpdate(**sr_payload)
                    )
                else:
                    await crud.create_screening_result(
                        db, ScreeningResultCreate(application_id=app_id, **sr_payload)
                    )

                # ── 6. Replace ApplicationDetail skill rows ────────────────────
                # (extracted already resolved above in step 1)
                if extracted and extracted.skills:
                    await db.execute(
                        delete(ApplicationDetail).where(
                            ApplicationDetail.application_id == app_id
                        )
                    )
                    await db.commit()

                    primary_edu  = extracted.education[0]      if extracted.education      else {}
                    primary_role = extracted.previous_roles[0] if extracted.previous_roles else {}

                    await crud.create_application_details_bulk(
                        db,
                        [
                            ApplicationDetailCreate(
                                application_id=app_id,
                                skill_name=skill,
                                years_of_experience=extracted.total_years_experience,
                                education_degree=primary_edu.get("degree"),
                                education_institution=primary_edu.get("institution"),
                                previous_company=primary_role.get("company"),
                                previous_role=primary_role.get("title"),
                            )
                            for skill in extracted.skills
                        ],
                    )

                saved += 1
                logger.info(f"[Node 4] Saved: source={source}, application_id={app_id}")

            except Exception as exc:
                state.error = f"[Node 4] DB operation failed for source={source}: {exc}"
                logger.error(state.error)
                return state

    logger.info(f"[Node 4] All results persisted — saved_count={saved}")

    state.saved_count = saved
    return state
