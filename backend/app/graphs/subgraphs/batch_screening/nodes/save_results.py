"""
Node 4 — Save Results to PostgreSQL (with re-screening support)

Responsibilities split by bucket (set by Node 2):

BUCKET A — existing candidates (is_existing_candidate=True / source in
           state.existing_candidate_sources):
  - Look up existing Application by lever_opportunity_id (already in DB)
  - Refresh scores on Application row
  - Update status based on new recommended_action
  - Upsert ScreeningResult (scores + justifications)
  - ApplicationDetail rows are NOT touched — data hasn't changed

BUCKET B — new candidates (is_existing_candidate=False):
  1. Candidate get-or-create:
       a. Valid extracted email + exists in state.email_to_candidate_id
          → reuse that existing candidate.id (candidate applied elsewhere before)
       b. Valid extracted email, not in mapping
          → create new Candidate row
       c. No valid email
          → create new Candidate row with placeholder email
  2. Create Application row
  3. Insert ApplicationDetail rows
  4. Create ScreeningResult row
  5. Transition Application status

Environment variables:
    DATABASE_URL (via database.py) — required
"""

import sys
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import delete

from db.database import AsyncSessionLocal                   # noqa: E402
from db.models import ApplicationDetail, ApplicationStatus  # noqa: E402
from db import crud                                         # noqa: E402
from schemas import (
    CandidateCreate,
    ApplicationCreate,
    ScreeningResultCreate,
    ScreeningResultUpdate,
    ApplicationDetailCreate,
)
from graphs.subgraphs.batch_screening.state import (  # noqa: E402
    BatchScreeningState,
    ExtractedCV,
)

logger = logging.getLogger(__name__)


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
    """Build flexible key/value detail rows from extracted CV data."""
    entries: list[ApplicationDetailCreate] = []

    if extracted.skills:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="technical_skills",
            value=extracted.skills,
            relevance="high",
        ))

    if extracted.total_years_experience:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="total_years_experience",
            value=extracted.total_years_experience,
            relevance="high",
        ))

    if extracted.education:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="education",
            value=extracted.education,
            relevance="medium",
        ))

    if extracted.previous_roles:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="previous_roles",
            value=extracted.previous_roles,
            relevance="medium",
        ))

    if extracted.certifications:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="certifications",
            value=extracted.certifications,
            relevance="medium",
        ))

    if extracted.summary:
        entries.append(ApplicationDetailCreate(
            application_id=app_id,
            key="profile_summary",
            value=extracted.summary,
            relevance="low",
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
            relevance="low",
        ))

    return entries


async def _upsert_screening_result(db, app_id: int, scored, now: datetime) -> None:
    """Create or update the ScreeningResult row for an application."""
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
        await crud.update_screening_result(db, app_id, ScreeningResultUpdate(**sr_payload))
    else:
        await crud.create_screening_result(
            db, ScreeningResultCreate(application_id=app_id, **sr_payload)
        )


async def _apply_status_transition(db, app_id: int, recommended_action: str) -> None:
    """Transition application status based on the LLM's recommended_action."""
    if recommended_action == "advance":
        await crud.update_application_status(db, app_id, ApplicationStatus.SCREENING_PASSED)
    elif recommended_action == "reject":
        await crud.update_application_status(db, app_id, ApplicationStatus.SCREENING_REJECTED)
    # "needs_review" → leave current status unchanged


# ── Main node ─────────────────────────────────────────────────────────────────

async def save_results_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 4: Persist all scoring results.

    Bucket A (existing applications) — update-only path:
        - Refresh scores on Application row
        - Upsert ScreeningResult
        - Update status

    Bucket B (new candidates) — full insert path:
        - Get-or-create Candidate (email-first, then create)
        - Create Application
        - Insert ApplicationDetail rows
        - Create ScreeningResult
        - Set initial status

    Reads:
        state.comparative_scores         — Node 3 output (full pool)
        state.extracted_cv_data          — Node 2 output (for detail insertion)
        state.existing_candidate_sources — Bucket A identifiers
        state.email_to_candidate_id      — Bucket B email → existing candidate.id

    Writes:
        state.saved_count   — new applications inserted (Bucket B)
        state.updated_count — existing applications refreshed (Bucket A)
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
        f"[Node 4: save_results] Persisting results for "
        f"{len(state.comparative_scores)} candidates "
        f"({scored_existing} updates, {scored_new} inserts)"
    )

    # Build lookup: source → ExtractedCV
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
                    # ── BUCKET A: update-only ─────────────────────────────────
                    lever_opp_id = f"screening_{state.requisition_id}_{source}"
                    application = await crud.get_application_by_lever_opportunity_id(
                        db, lever_opp_id
                    )
                    if not application:
                        # Defensive — should never happen for Bucket A
                        logger.warning(
                            f"[Node 4] Bucket A: application not found for "
                            f"source='{source}' lever_opp_id='{lever_opp_id}' — skipping update"
                        )
                        continue

                    app_id = application.id
                    scored.application_id = app_id

                    # Refresh scores
                    application.cosine_similarity_score = scored.cosine_similarity_score
                    application.technical_score         = scored.technical_score
                    application.behavioral_score        = scored.behavioral_score
                    application.combined_score          = scored.combined_score
                    application.last_activity_at        = now
                    await db.commit()

                    # Update status
                    await _apply_status_transition(db, app_id, scored.recommended_action)

                    # Upsert ScreeningResult
                    await _upsert_screening_result(db, app_id, scored, now)

                    updated += 1
                    logger.info(
                        f"[Node 4] Updated: source='{source}', "
                        f"application_id={app_id}, "
                        f"combined={scored.combined_score:.4f}"
                    )

                else:
                    # ── BUCKET B: full insert ─────────────────────────────────
                    extracted = cv_lookup.get(source)
                    if extracted is None:
                        logger.warning(
                            f"[Node 4] Bucket B: no ExtractedCV for source='{source}' "
                            "— skipping insert"
                        )
                        continue

                    # ── 1. Resolve candidate ──────────────────────────────────
                    # Priority order:
                    #   a) Email matched an existing global candidate (Node 2 found them)
                    #   b) Create new candidate (fresh or placeholder email)
                    extracted_email = extracted.email or ""
                    email_is_valid = _valid_email(extracted_email) and \
                                     "@screening.internal" not in extracted_email

                    existing_candidate_id = (
                        state.email_to_candidate_id.get(extracted_email)
                        if email_is_valid else None
                    )

                    if existing_candidate_id:
                        # Reuse existing candidate row
                        candidate = await crud.get_candidate_by_id(db, existing_candidate_id)
                        if not candidate:
                            # Race condition safety — fall through to create
                            logger.warning(
                                f"[Node 4] email_to_candidate_id pointed to "
                                f"candidate_id={existing_candidate_id} but row not found "
                                "— will create new candidate"
                            )
                            existing_candidate_id = None

                    if not existing_candidate_id:
                        # Build identity fields
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
                        candidate = await crud.get_or_create_candidate(
                            db,
                            CandidateCreate(
                                full_name=full_name,
                                email=email,
                                phone=extracted.phone,
                                linkedin_url=extracted.linkedin_url,
                                lever_id=source,
                            ),
                        )

                    # ── 2. Create Application ─────────────────────────────────
                    lever_opp_id = f"screening_{state.requisition_id}_{source}"
                    # Guard: don't create a duplicate if one slipped through
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
                    scored.application_id = app_id

                    # ── 3. Write scores to Application ────────────────────────
                    application.cosine_similarity_score = scored.cosine_similarity_score
                    application.technical_score         = scored.technical_score
                    application.behavioral_score        = scored.behavioral_score
                    application.combined_score          = scored.combined_score
                    application.last_activity_at        = now
                    await db.commit()

                    # ── 4. Status transition ──────────────────────────────────
                    await _apply_status_transition(db, app_id, scored.recommended_action)

                    # ── 5. ScreeningResult ────────────────────────────────────
                    await _upsert_screening_result(db, app_id, scored, now)

                    # ── 6. ApplicationDetail rows ─────────────────────────────
                    # Delete any stale rows first (idempotent re-run safety),
                    # then bulk insert fresh detail entries.
                    await db.execute(
                        delete(ApplicationDetail).where(
                            ApplicationDetail.application_id == app_id
                        )
                    )
                    await db.commit()

                    detail_entries = _build_application_detail_entries(app_id, extracted)
                    if detail_entries:
                        await crud.create_application_details_bulk(db, detail_entries)

                    saved += 1
                    logger.info(
                        f"[Node 4] Inserted: source='{source}', "
                        f"candidate_id={candidate.id}, "
                        f"application_id={app_id}, "
                        f"combined={scored.combined_score:.4f}"
                    )

            except Exception as exc:
                state.error = (
                    f"[Node 4] DB operation failed for source='{source}': {exc}"
                )
                logger.error(state.error)
                return state

    logger.info(
        f"[Node 4] Complete — inserted={saved}, updated={updated}"
    )
    state.saved_count   = saved
    state.updated_count = updated
    return state