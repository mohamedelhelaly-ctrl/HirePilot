"""
Node 2b — Interview Enrichment

For interview_rescreen mode, loads completed interview summaries per candidate
and attaches them to state for the comparative scorer.

Pass-through for new_candidates mode (CV-only scoring unchanged).
"""

import logging

from models.database import AsyncSessionLocal
from models.crud.application_crud import get_application_by_lever_opportunity_id
from models.crud.interview_session_crud import get_interview_sessions_by_application
from models.tables_enums import InterviewStatus
from ..batchScreening_state import BatchScreeningState

logger = logging.getLogger(__name__)


def _build_session_payload(session) -> dict:
    return {
        "type": session.interview_type.value if session.interview_type else None,
        "recommendation_score": session.recommendation_score,
        "technical_depth_score": session.technical_depth_score,
        "summary": session.summary,
        "key_strengths": session.key_strengths or [],
        "key_concerns": session.key_concerns or [],
        "overall_assessment": session.overall_assessment,
    }


async def interview_enrichment_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Load interview context for each candidate in the pool (interview_rescreen only).
    """
    if state.error:
        return state

    if state.screening_mode != "interview_rescreen":
        logger.info("[Node 2b: interview_enrichment] Skipped — new_candidates mode")
        return state

    if not state.extracted_cv_data:
        state.error = "[Node 2b] No extracted CV data — cannot enrich interviews"
        logger.error(state.error)
        return state

    logger.info(
        f"[Node 2b: interview_enrichment] Enriching {len(state.extracted_cv_data)} candidates"
    )

    interview_context: dict[str, dict] = {}

    async with AsyncSessionLocal() as db:
        for cv in state.extracted_cv_data:
            lever_opp_id = f"screening_{state.requisition_id}_{cv.source}"
            application = await get_application_by_lever_opportunity_id(db, lever_opp_id)
            if not application:
                logger.warning(
                    f"[Node 2b] No application for source='{cv.source}' — skipping interviews"
                )
                continue

            sessions = await get_interview_sessions_by_application(db, application.id)
            completed = [
                s for s in sessions
                if s.status == InterviewStatus.COMPLETED
            ]

            interview_context[cv.source] = {
                "interview_count": len(completed),
                "overall_interview_score": application.overall_interview_score,
                "sessions": [_build_session_payload(s) for s in completed],
            }

    state.interview_context_by_source = interview_context
    with_interviews = sum(
        1 for ctx in interview_context.values() if ctx.get("interview_count", 0) > 0
    )
    logger.info(
        f"[Node 2b] Enrichment complete — {with_interviews}/{len(state.extracted_cv_data)} "
        "candidates have interview data"
    )
    return state
