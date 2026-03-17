"""
RAG Query Subgraph

Assembles the 3-node LangGraph pipeline and exports a compiled singleton
that can be invoked by the outer orchestrator.

Graph structure:
                        ┌───────────────────┐
                        │       START       │
                        └────────┬──────────┘
                                 │
                                 ▼
                   ┌─────────────────────────────┐
                   │   query_processing_node     │  Node 1
                   │  Extract filters, vectorize │
                   └────────┬────────────┬────────┘
                            │ (continue) │ (error)
                            ▼            ▼
                   ┌────────────────┐   END
                   │ retrieval_and_ │  Node 2
                   │ context_node   │
                   │ ChromaDB + DB  │
                   └───┬────────┬───┘
                  (cont)│  (err)│
                        ▼       ▼
              ┌───────────────────┐  END
              │ response_          │  Node 3
              │ generation_node   │
              │  LLM answer + cite │
              └──────┬─────────────┘
                     │
                     ▼
                    END

Exported symbol:
    rag_query_subgraph — compiled CompiledStateGraph, ready for .invoke()

Usage (from nodes/rag_query.py):
    from .subgraphs.rag_query.graph import rag_query_subgraph
    from .subgraphs.rag_query.state import RAGQueryState

    result_state = await rag_query_subgraph.ainvoke(
        RAGQueryState(query="Who are the top Python developers?", requisition_id=1)
    )
"""

import logging
from langgraph.graph import StateGraph, END

from .state import RAGQueryState
from .nodes.query_processing import query_processing_node
from .nodes.retrieval_and_context import retrieval_and_context_node
from .nodes.response_generation import response_generation_node

logger = logging.getLogger(__name__)


# ── Conditional edge function ─────────────────────────────────────────────────

def _route_on_error(state: RAGQueryState) -> str:
    """
    Return "error" if state.error is set (routes to END immediately),
    otherwise return "continue" to advance to the next node.
    """
    if state.error:
        logger.warning(f"[RAG Query Graph] Routing to END due to error: {state.error}")
        return "error"
    return "continue"


# ── Graph builder ─────────────────────────────────────────────────────────────

def create_rag_query_subgraph():
    """
    Build and compile the RAG query LangGraph subgraph.
    
    Returns:
        CompiledStateGraph — ready to call via .invoke() or .ainvoke()
    """
    workflow = StateGraph(RAGQueryState)
    
    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("query_processing", query_processing_node)
    workflow.add_node("retrieval_and_context", retrieval_and_context_node)
    workflow.add_node("response_generation", response_generation_node)
    
    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("query_processing")
    
    # ── Conditional edges (fail-fast: END on any error) ───────────────────────
    workflow.add_conditional_edges(
        "query_processing",
        _route_on_error,
        {"error": END, "continue": "retrieval_and_context"},
    )
    workflow.add_conditional_edges(
        "retrieval_and_context",
        _route_on_error,
        {"error": END, "continue": "response_generation"},
    )
    
    # response_generation always goes to END (its own errors are in state.error)
    workflow.add_edge("response_generation", END)
    
    return workflow.compile()


# ── Compiled singleton ────────────────────────────────────────────────────────

rag_query_subgraph = create_rag_query_subgraph()

logger.info("RAG Query subgraph compiled successfully")
