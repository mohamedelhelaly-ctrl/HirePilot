"""
Node 2 — Save Interview Results

Responsibilities:
1. Update InterviewSession row with summary, scores, transcript, status → COMPLETED
2. Update Application row: overall_interview_score, last_interview_completed_at,
   status → INTERVIEW_COMPLETED
3. Increment new_interview_counter on Requisition
4. (disabled) If counter >= threshold → trigger batch screening
"""

import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from models.database import AsyncSessionLocal
from models.schemas import InterviewSessionUpdate
from models.tables_enums import InterviewStatus, ApplicationStatus
from ..liveInterview_state import LiveInterviewState

from controllers import ApplicationController, RequisitionController, InterviewController
application_controller = ApplicationController()
req_controller = RequisitionController()
interview_controller = InterviewController()

logger = logging.getLogger(__name__)


# Disabled until interview screening threshold is decided.
# async def _trigger_background_screening(requisition_id: int) -> None:
#     """Run batch screening on a dedicated DB session (never share the save session)."""
#     from graphs.maingraph import main_graph
#     from graphs.state import OrchestratorState
#
#     try:
#         async with AsyncSessionLocal() as db:
#             await req_controller.set_screening_in_progress(
#                 db, requisition_id, value=True
#             )
#
#         graph_state = OrchestratorState(
#             intent="batch_screening",
#             requisition_id=requisition_id,
#             manual_trigger=False,
#         )
#         raw = await main_graph.ainvoke(graph_state)
#         final = (
#             raw if isinstance(raw, OrchestratorState)
#             else OrchestratorState(**raw)
#         )
#         success = not bool(final.error)
#
#         async with AsyncSessionLocal() as db:
#             await req_controller.set_screening_in_progress(
#                 db, requisition_id,
#                 value=False,
#                 reset_counter=success,
#             )
#     except Exception as exc:
#         logger.error(
#             f"[Node 2] Background screening trigger failed: {exc}",
#             exc_info=True,
#         )
#         try:
#             async with AsyncSessionLocal() as db:
#                 await req_controller.set_screening_in_progress(
#                     db, requisition_id, value=False
#                 )
#         except Exception:
#             pass


async def save_interview_node(state: LiveInterviewState) -> LiveInterviewState:
    """
    Node 2: Persist all interview results to PostgreSQL.
    (Post-interview batch screening trigger is disabled for now.)

    Reads:
        state.session_id
        state.application_id
        state.requisition_id
        state.full_transcript
        state.summary, state.overall_assessment
        state.key_strengths, state.key_concerns
        state.recommendation_score, state.technical_depth_score
        state.qa_pairs
        state.followup_questions_log
        state.interview_end_time

    Writes:
        state.saved = True on success
    """
    if state.error:
        return state

    now = datetime.now(timezone.utc)

    try:
        async with AsyncSessionLocal() as db:

            # ── 1. Update InterviewSession ─────────────────────────────────────
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

            # ── 2. Update Application ──────────────────────────────────────────
            application = await application_controller.get_application(state.application_id, db)
            if application:
                application.last_interview_completed_at = now
                application.overall_interview_score     = state.recommendation_score
                application.last_activity_at            = now
                await db.commit()

                await application_controller.update_application_status(
                    state.application_id,
                    ApplicationStatus.INTERVIEW_COMPLETED,
                    db
                )
                logger.info(
                    f"[Node 2] Application {state.application_id} updated — "
                    f"overall_interview_score={state.recommendation_score}"
                )
            else:
                logger.warning(
                    f"[Node 2] Application {state.application_id} not found — "
                    "skipping application update"
                )

            # ── 3. Increment interview counter ────────────────────────────────
            requisition = await req_controller.increment_requisition_counter(
                db, state.requisition_id, "interview"
            )
            logger.info(
                f"[Node 2] Interview counter incremented for "
                f"requisition_id={state.requisition_id} — "
                f"counter={requisition.new_interview_counter if requisition else '?'}"
            )

            # ── 4. Check threshold → trigger batch screening (disabled) ───────
            # if (
            #     requisition
            #     and requisition.new_interview_counter >= requisition.new_interview_threshold
            #     and not requisition.screening_in_progress
            # ):
            #     should_trigger_screening = True
            #     logger.info(
            #         f"[Node 2] Interview threshold met for "
            #         f"requisition_id={state.requisition_id} — "
            #         "will trigger batch screening after save"
            #     )

        state.saved = True
        logger.info(f"[Node 2] Interview results saved for session_id={state.session_id}")

    except Exception as exc:
        state.error = f"[Node 2] DB save failed: {exc}"
        logger.error(state.error, exc_info=True)
        return state

    # if should_trigger_screening:
    #     import asyncio
    #     asyncio.create_task(_trigger_background_screening(state.requisition_id))

    return state

