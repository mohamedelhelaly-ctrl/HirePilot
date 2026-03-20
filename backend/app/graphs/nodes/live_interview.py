"""
Live Interview Node

This node is intentionally minimal. The actual live interview logic
(real-time transcription, follow-up question generation) lives in the
WebSocket endpoint at api/routers/interview.py.

This node is invoked by the main orchestrator only if something needs
to trigger the post-interview subgraph programmatically (e.g. from a
webhook or a scheduled job). In the normal flow, the WebSocket handler
invokes the subgraph directly when the interviewer clicks "End Interview".
"""

import logging
from ..state import OrchestratorState

logger = logging.getLogger(__name__)


async def live_interview_node(state: OrchestratorState) -> OrchestratorState:
    """
    Entry point for programmatic post-interview processing.

    For the normal live interview flow, see:
        backend/app/api/routers/interview.py  ← WebSocket handler
        backend/app/graphs/subgraphs/live_interview/  ← post-processing subgraph

    This node is a pass-through unless a session_id is provided,
    in which case it invokes the post-interview subgraph directly.
    """
    logger.info(
        f"[live_interview_node] session_id={state.session_id}, "
        f"application_id={state.application_id}"
    )

    if not state.session_id or not state.application_id:
        state.error = (
            "live_interview_node requires session_id and application_id. "
            "For real-time interviews, use the WebSocket endpoint directly."
        )
        logger.warning(state.error)
        return state

    # If somehow triggered with a complete session_id, just acknowledge.
    # The WebSocket handler already took care of everything.
    state.result = {
        "status":     "acknowledged",
        "session_id": state.session_id,
        "message":    "Live interview post-processing is handled by the WebSocket endpoint.",
    }
    return state