"""
Batch Screening Subgraph

Assembles the 4-node LangGraph pipeline and exports a compiled singleton
that can be invoked by the outer orchestrator.

Structure:
    1- START
    2- Similarity Search with JD (top k vectordb retrievals)
    3- CV extraction using LLM
    4- comparative scoring
    5- Save Results to database
    6- END

"""

import logging
from langgraph.graph import StateGraph, END

from .batchScreening_state import BatchScreeningState
from .batchScreening_nodes  import similarity_search_node, cv_extraction_node, comparative_scoring_node, save_results_node

logger = logging.getLogger(__name__)


# ── Conditional edge function ─────────────────────────────────────────────────
def _route_on_error(state: BatchScreeningState) -> str:
    if state.error:
        logger.warning(f"[Graph] Routing to END due to error: {state.error}")
        return "error"
    return "continue"


# ── Graph builder ─────────────────────────────────────────────────────────────
def create_batch_screening_subgraph():

    workflow = StateGraph(BatchScreeningState)

    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("similarity_search",    similarity_search_node)
    workflow.add_node("cv_extraction",         cv_extraction_node)
    workflow.add_node("comparative_scoring",   comparative_scoring_node)
    workflow.add_node("save_results",          save_results_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("similarity_search")


    # ── Conditional edges ───────────────────────
    workflow.add_conditional_edges(
        "similarity_search",
        _route_on_error,
        {"error": END, "continue": "cv_extraction"},
    )
    workflow.add_conditional_edges(
        "cv_extraction",
        _route_on_error,
        {"error": END, "continue": "comparative_scoring"},
    )
    workflow.add_conditional_edges(
        "comparative_scoring",
        _route_on_error,
        {"error": END, "continue": "save_results"},
    )

    # save_results always goes to END (its own errors are in state.error)
    workflow.add_edge("save_results", END)

    return workflow.compile()


# ── Compiled singleton ────────────────────────────────────────────────────────
batch_screening_subgraph = create_batch_screening_subgraph()
