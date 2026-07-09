"""
Live Interview Post-Processing Subgraph

Invoked ONCE when the interviewer clicks "End Interview".
Receives the complete transcript and session context from the WebSocket handler,
generates a summary + scores, then persists everything to the DB.

Graph:
    START → generate_summary → save_interview → END
                  ↓ (error)
                 END
"""

import logging
from langgraph.graph import StateGraph, END

from .liveInterview_state import LiveInterviewState
from .liveInterview_nodes.generate_summary import generate_summary_node
from .liveInterview_nodes.save_interview import save_interview_node

logger = logging.getLogger(__name__)


def _route_on_error(state: LiveInterviewState) -> str:
    if state.error:
        logger.warning(f"[LiveInterviewGraph] Routing to END due to error: {state.error}")
        return "error"
    return "continue"


def create_live_interview_subgraph():
    workflow = StateGraph(LiveInterviewState)

    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("save_interview",   save_interview_node)

    workflow.set_entry_point("generate_summary")

    workflow.add_conditional_edges(
        "generate_summary",
        _route_on_error,
        {"error": END, "continue": "save_interview"},
    )
    workflow.add_edge("save_interview", END)

    return workflow.compile()


# Compiled singleton — stateless, safe to share across requests
live_interview_subgraph = create_live_interview_subgraph()