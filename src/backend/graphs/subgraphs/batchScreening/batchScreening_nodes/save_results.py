"""
Node 4 — Save Results to PostgreSQL (with re-screening support)

BUCKET A — existing candidates:
  - Refresh combined_score on Application row
  - Upsert ScreeningResult (score + justification)
  - ApplicationDetail rows are NOT touched

BUCKET B — new candidates:
  1. Candidate get-or-create (email-first lookup)
  2. Create Application row
  3. Insert ApplicationDetail rows
  4. Create ScreeningResult row

Application status is left unchanged after screening — HR sets it manually.
"""

import sys
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import delete

from models.database import AsyncSessionLocal
from models.tables.application_detail import ApplicationDetail

from models.schemas import (
    CandidateCreate,
    ApplicationCreate,
    ScreeningResultCreate,
    ScreeningResultUpdate,
    ApplicationDetailCreate,
)
from ..batchScreening_state import BatchScreeningState, ExtractedCV

logger = logging.getLogger(__name__)

from controllers.ApplicationController import ApplicationController
from controllers.CandidateController import CandidateController
application_controller = ApplicationController()
candidate_controller = CandidateController()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _valid_email(addr: str) -> bool:
    parts = addr.split("@")
    return (
        len(parts) == 2
        and bool(parts[0].strip())
        and bool(parts[1].strip())
        and " " not in addr
    )


def _build_application_detail_entries(
    app_id: int, extracted: ExtractedCV
) -> list[ApplicationDetailCreate]:
    """Build key/value detail rows from extracted CV data."""
    entries: list[ApplicationDetailCreate] = []

    if extracted.skills:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="technical_skills",
            value=extracted.skills,
        ))

    if extracted.total_years_experience:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="total_years_experience",
            value=extracted.total_years_experience,
        ))

    if extracted.education:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="education",
            value=extracted.education,
        ))

    if extracted.previous_roles:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="previous_roles",
            value=extracted.previous_roles,
        ))

    if extracted.certifications:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="certifications",
            value=extracted.certifications,
        ))

    if extracted.summary:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="profile_summary",
            value=extracted.summary,
        ))

    contact_info = {
        "phone":        extracted.phone,
        "linkedin_url": extracted.linkedin_url,
        "email":        extracted.email,
    }
    if any(contact_info.values()):
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="contact_info",
            value=contact_info,
        ))

    return entries


async def _upsert_screening_result(db, app_id: int, scored) -> None:
    """Create or update the ScreeningResult row for an application."""
    sr_payload = dict(
        score=scored.combined_score,
        justification=scored.justification,
    )
    existing_sr = await application_controller.get_screening_result_by_applicationId(db, app_id)
    if existing_sr:
        await application_controller.update_screening_result(db, app_id, ScreeningResultUpdate(**sr_payload) )
    else:
        await application_controller.create_screening_result(db, ScreeningResultCreate(application_id=app_id, **sr_payload))


# Main node

async def save_results_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 4: Persist all scoring results to PostgreSQL.

    Reads:
        state.comparative_scores         — Node 3 output
        state.extracted_cv_data          — Node 2 output (for detail insertion)
        state.existing_candidate_sources — Bucket A identifiers
        state.email_to_candidate_id      — Bucket B email → existing candidate.id

    Writes:
        state.saved_count   — new applications inserted
        state.updated_count — existing applications refreshed
    """
    if state.error:
        return state

    if not state.comparative_scores:
        state.error = "[Node 4] No scores to save — comparative_scores is empty"
        logger.error(state.error)
        return state

    scored_existing = sum(
        1 for s in state.comparative_scores
        if s.source in state.existing_candidate_sources
    )
    scored_new = len(state.comparative_scores) - scored_existing
    logger.info(
        f"[Node 4: save_results] Persisting {len(state.comparative_scores)} candidates "
        f"({scored_existing} updates, {scored_new} inserts)"
    )

    cv_lookup: dict[str, ExtractedCV] = {
        cv.source: cv for cv in state.extracted_cv_data
    }

    now = datetime.now(timezone.utc)
    saved = 0
    updated = 0

    async with AsyncSessionLocal() as db:
        for scored in state.comparative_scores:
            source = scored.source
            is_existing = source in state.existing_candidate_sources

            try:
                if is_existing:
                    # ── BUCKET A: update only ─────────────────────────────────
                    lever_opp_id = f"screening_{state.requisition_id}_{source}"
                    application = await application_controller.get_application_by_lever_opportunity_id(
                        db, lever_opp_id
                    )
                    if not application:
                        logger.warning(
                            f"[Node 4] Bucket A: application not found for "
                            f"source='{source}' — skipping update"
                        )
                        continue

                    app_id = application.id
                    scored.application_id = app_id

                    application.combined_score   = scored.combined_score
                    application.last_activity_at = now
                    extracted_a = cv_lookup.get(source)
                    if extracted_a and extracted_a.total_years_experience:
                        application.years_of_experience = extracted_a.total_years_experience
                    await db.commit()

                    await _upsert_screening_result(db, app_id, scored)

                    updated += 1
                    logger.info(
                        f"[Node 4] Updated: source='{source}', "
                        f"application_id={app_id}, score={scored.combined_score:.4f}"
                    )

                else:
                    # ── BUCKET B: full insert ─────────────────────────────────
                    extracted = cv_lookup.get(source)
                    if extracted is None:
                        logger.warning(
                            f"[Node 4] Bucket B: no ExtractedCV for source='{source}' — skipping"
                        )
                        continue

                    # 1. Resolve candidate
                    extracted_email = extracted.email or ""
                    email_is_valid = (
                        _valid_email(extracted_email)
                        and "@screening.internal" not in extracted_email
                    )
                    existing_candidate_id = (
                        state.email_to_candidate_id.get(extracted_email)
                        if email_is_valid else None
                    )

                    if existing_candidate_id:
                        candidate = await candidate_controller.get_candidate(existing_candidate_id, db)
                        if not candidate:
                            logger.warning(
                                f"[Node 4] email_to_candidate_id pointed to "
                                f"candidate_id={existing_candidate_id} but row not found "
                                "— creating new candidate"
                            )
                            existing_candidate_id = None

                    if not existing_candidate_id:
                        filename_stem = Path(source).stem
                        full_name = (
                            extracted.full_name
                            if extracted.full_name
                            else filename_stem.replace("_", " ").replace("-", " ").title()
                        )
                        safe_stem = re.sub(r"[^a-z0-9]+", "-", filename_stem.lower()).strip("-")
                        email = (
                            extracted_email
                            if email_is_valid
                            else f"{safe_stem}@screening.internal"
                        )
                        candidate = await candidate_controller.get_or_create_candidate(
                            db,
                            CandidateCreate(
                                full_name=full_name,
                                email=email,
                                phone=extracted.phone,
                                linkedin_url=extracted.linkedin_url,
                                lever_id=source,
                            )
                        )

                    # 2. Create Application
                    lever_opp_id = f"screening_{state.requisition_id}_{source}"
                    application = await application_controller.get_application_by_lever_opportunity_id(db, lever_opp_id)
                    if not application:
                        application = await application_controller.create_application(
                            ApplicationCreate(
                                candidate_id=candidate.id,
                                requisition_id=state.requisition_id,
                                lever_opportunity_id=lever_opp_id,
                                years_of_experience=extracted.total_years_experience or None,
                            ),
                            db
                        )

                    app_id = application.id
                    scored.application_id = app_id

                    # 3. Write score
                    application.combined_score   = scored.combined_score
                    application.last_activity_at = now
                    await db.commit()

                    # 4. ScreeningResult
                    await _upsert_screening_result(db, app_id, scored)

                    # 5. ApplicationDetail rows
                    await db.execute(
                        delete(ApplicationDetail).where(
                            ApplicationDetail.application_id == app_id
                        )
                    )
                    await db.commit()

                    detail_entries = _build_application_detail_entries(app_id, extracted)
                    if detail_entries:
                        await application_controller.create_many_application_details(db, detail_entries)

                    saved += 1
                    logger.info(
                        f"[Node 4] Inserted: source='{source}', "
                        f"candidate_id={candidate.id}, "
                        f"application_id={app_id}, score={scored.combined_score:.4f}"
                    )

            except Exception as exc:
                state.error = f"[Node 4] DB operation failed for source='{source}': {exc}"
                logger.error(state.error)
                return state

    logger.info(f"[Node 4] Complete — inserted={saved}, updated={updated}")
    state.saved_count   = saved
    state.updated_count = updated
    return state