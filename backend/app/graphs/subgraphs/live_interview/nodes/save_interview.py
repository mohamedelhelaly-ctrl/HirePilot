"""
Node 2 — Save Interview Results

Responsibilities:
1. Update InterviewSession row with summary, scores, transcript, status → COMPLETED
2. Update Application row: overall_interview_score, last_interview_completed_at,
   status → INTERVIEW_COMPLETED
3. Increment new_interview_counter on Requisition
4. If counter >= threshold → trigger batch screening (background, non-blocking)
"""

import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from db.database import AsyncSessionLocal
from db import crud
from db.models import InterviewStatus, ApplicationStatus
from schemas import InterviewSessionUpdate
from ..state import LiveInterviewState

logger = logging.getLogger(__name__)


async def save_interview_node(state: LiveInterviewState) -> LiveInterviewState:
    """
    Node 2: Persist all interview results to PostgreSQL and trigger
    re-screening if the interview threshold is met.

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
            await crud.update_interview_session(db, state.session_id, session_update)
            logger.info(f"[Node 2] InterviewSession {state.session_id} updated")

            # ── 2. Update Application ──────────────────────────────────────────
            application = await crud.get_application_by_id(db, state.application_id)
            if application:
                application.last_interview_completed_at = now
                application.overall_interview_score     = state.recommendation_score
                application.last_activity_at            = now
                await db.commit()

                await crud.update_application_status(
                    db,
                    state.application_id,
                    ApplicationStatus.INTERVIEW_COMPLETED,
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
            requisition = await crud.increment_requisition_counter(
                db, state.requisition_id, "interview"
            )
            logger.info(
                f"[Node 2] Interview counter incremented for "
                f"requisition_id={state.requisition_id} — "
                f"counter={requisition.new_interview_counter if requisition else '?'}"
            )

            # ── 4. Check threshold → trigger batch screening ──────────────────
            if (
                requisition
                and requisition.new_interview_counter >= requisition.new_interview_threshold
                and not requisition.screening_in_progress
            ):
                logger.info(
                    f"[Node 2] Interview threshold met for "
                    f"requisition_id={state.requisition_id} — "
                    "triggering batch screening in background"
                )
                # Fire-and-forget — import here to avoid circular imports
                import asyncio
                from graphs.main_graph import main_graph
                from graphs.state import OrchestratorState

                async def _trigger():
                    try:
                        await crud.set_screening_in_progress(
                            db, state.requisition_id, value=True
                        )
                        graph_state = OrchestratorState(
                            intent="batch_screening",
                            requisition_id=state.requisition_id,
                            manual_trigger=False,
                        )
                        raw = await main_graph.ainvoke(graph_state)
                        final = (
                            raw if isinstance(raw, OrchestratorState)
                            else OrchestratorState(**raw)
                        )
                        success = not bool(final.error)
                        await crud.set_screening_in_progress(
                            db, state.requisition_id,
                            value=False,
                            reset_counter=success,
                        )
                    except Exception as exc:
                        logger.error(
                            f"[Node 2] Background screening trigger failed: {exc}"
                        )
                        try:
                            await crud.set_screening_in_progress(
                                db, state.requisition_id, value=False
                            )
                        except Exception:
                            pass

                asyncio.create_task(_trigger())

        state.saved = True
        logger.info(f"[Node 2] Interview results saved for session_id={state.session_id}")

    except Exception as exc:
        state.error = f"[Node 2] DB save failed: {exc}"
        logger.error(state.error, exc_info=True)

    return state