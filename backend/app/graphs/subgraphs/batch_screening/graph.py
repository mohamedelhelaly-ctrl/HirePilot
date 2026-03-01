"""
Batch Screening Subgraph

Assembles the 4-node LangGraph pipeline and exports a compiled singleton
that can be invoked by the outer orchestrator.

Graph structure:
                        ┌───────────────────┐
                        │       START       │
                        └────────┬──────────┘
                                 │
                                 ▼
                   ┌─────────────────────────────┐
                   │   similarity_search_node     │  Node 1
                   │  ChromaDB top-20 retrieval   │
                   └────────┬────────────┬────────┘
                            │ (continue) │ (error)
                            ▼            ▼
                   ┌────────────────┐   END
                   │ cv_extraction  │  Node 2
                   │  GROQ parallel │
                   └───┬────────┬───┘
                  (cont)│  (err)│
                        ▼       ▼
              ┌───────────────────┐  END
              │ comparative_       │  Node 3
              │ scoring_node      │
              │  GROQ single call │
              └──────┬───────┬────┘
               (cont)│  (err)│
                     ▼       ▼
            ┌──────────────────┐  END
            │ save_results_node│  Node 4
            │  PostgreSQL upsert│
            └────────┬─────────┘
                     │
                     ▼
                    END

Exported symbol:
    batch_screening_subgraph — compiled CompiledStateGraph, ready for .invoke()

Usage (from nodes/batch_screening.py):
    from .subgraphs.batch_screening.graph import batch_screening_subgraph
    from .subgraphs.batch_screening.state import BatchScreeningState

    result_state = await batch_screening_subgraph.ainvoke(
        BatchScreeningState(requisition_id=42)
    )
"""

import logging
from langgraph.graph import StateGraph, END

from .state import BatchScreeningState
from .nodes.similarity_search   import similarity_search_node
from .nodes.cv_extraction        import cv_extraction_node
from .nodes.comparative_scoring  import comparative_scoring_node
from .nodes.save_results         import save_results_node

logger = logging.getLogger(__name__)


# ── Conditional edge function ─────────────────────────────────────────────────

def _route_on_error(state: BatchScreeningState) -> str:
    """
    Return "error" if state.error is set (routes to END immediately),
    otherwise return "continue" to advance to the next node.
    """
    if state.error:
        logger.warning(f"[Graph] Routing to END due to error: {state.error}")
        return "error"
    return "continue"


# ── Graph builder ─────────────────────────────────────────────────────────────

def create_batch_screening_subgraph():
    """
    Build and compile the batch screening LangGraph subgraph.

    Returns:
        CompiledStateGraph — ready to call via .invoke() or .ainvoke()
    """
    workflow = StateGraph(BatchScreeningState)

    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("similarity_search",    similarity_search_node)
    workflow.add_node("cv_extraction",         cv_extraction_node)
    workflow.add_node("comparative_scoring",   comparative_scoring_node)
    workflow.add_node("save_results",          save_results_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("similarity_search")

    # ── Conditional edges (fail-fast: END on any error) ───────────────────────
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
# Built once at import time; reused across all invocations.
# LangGraph compiled graphs are stateless — safe to share across requests.
batch_screening_subgraph = create_batch_screening_subgraph()
