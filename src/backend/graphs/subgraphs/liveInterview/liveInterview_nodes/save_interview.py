"""
Node 2 — Save Interview Results

Responsibilities:
1. Update InterviewSession row with summary, scores, transcript, status → COMPLETED
2. Update Application row: overall_interview_score, last_interview_completed_at
3. If every screened candidate has completed an interview → trigger interview rescreen
"""

import asyncio
import logging
from datetime import datetime, timezone

from models.database import AsyncSessionLocal
from models.schemas import InterviewSessionUpdate
from models.schemas.application_schemas import ApplicationUpdate
from models.crud.application_crud import update_application as update_application_crud
from models.tables_enums import InterviewStatus, ApplicationStatus
from services.screening_helpers import requisition_ready_for_interview_rescreen
from ..liveInterview_state import LiveInterviewState

from controllers import ApplicationController, InterviewController

application_controller = ApplicationController()
interview_controller = InterviewController()

logger = logging.getLogger(__name__)


async def save_interview_node(state: LiveInterviewState) -> LiveInterviewState:
    """Node 2: Persist all interview results to PostgreSQL."""
    if state.error:
        return state

    now = datetime.now(timezone.utc)
    should_trigger_rescreen = False

    try:
        async with AsyncSessionLocal() as db:
            qa_pairs_serialised = [
                {
                    "question": qa.question,
                    "answer":   qa.answer,
                    "score":    qa.score,
                    "feedback": qa.feedback,
                }
                for qa in state.qa_pairs
            ]

            session_update = InterviewSessionUpdate(
                status=InterviewStatus.COMPLETED,
                actual_end_time=now,
                full_transcript=state.full_transcript,
                summary=state.summary,
                overall_assessment=state.overall_assessment,
                key_strengths=state.key_strengths,
                key_concerns=state.key_concerns,
                recommendation_score=state.recommendation_score,
                technical_depth_score=state.technical_depth_score,
                generated_followup_questions=state.followup_questions_log,
            )
            await interview_controller.update_interview_session(state.session_id, session_update, db)
            logger.info(f"[Node 2] InterviewSession {state.session_id} updated")

            application_update = ApplicationUpdate(
                overall_interview_score=state.recommendation_score,
                last_interview_completed_at=now,
            )
            updated = await update_application_crud(
                db, state.application_id, application_update
            )
            if updated:
                await application_controller.update_application_status(
                    state.application_id,
                    ApplicationStatus.INTERVIEW_COMPLETED,
                    db,
                )
                logger.info(
                    f"[Node 2] Application {state.application_id} updated — "
                    f"overall_interview_score={state.recommendation_score}, "
                    f"last_interview_completed_at={now.isoformat()}"
                )
            else:
                logger.warning(
                    f"[Node 2] Application {state.application_id} not found — "
                    "skipping application update"
                )

            if await requisition_ready_for_interview_rescreen(db, state.requisition_id):
                should_trigger_rescreen = True
                logger.info(
                    f"[Node 2] All screened candidates interviewed for "
                    f"requisition_id={state.requisition_id} — "
                    "will trigger interview rescreen after save"
                )

        state.saved = True
        logger.info(f"[Node 2] Interview results saved for session_id={state.session_id}")

    except Exception as exc:
        state.error = f"[Node 2] DB save failed: {exc}"
        logger.error(state.error, exc_info=True)
        return state

    if should_trigger_rescreen:
        from services.screening_runner import run_screening

        asyncio.create_task(
            run_screening(state.requisition_id, "interview_rescreen")
        )

    return state
