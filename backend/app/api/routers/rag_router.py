"""
RAG Query Router

Test/development endpoint to exercise the full rag_query flow through the
main orchestration graph.

POST /api/rag/query
    - Accepts query text + requisition_id + optional user_id
    - Builds OrchestratorState with intent="rag_query"
    - Invokes main_graph.ainvoke()
    - Returns the LLM response or error
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from graphs.main_graph import main_graph
from graphs.state import OrchestratorState

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    query: str
    requisition_id: int
    user_id: Optional[int] = None


class RAGQueryResponse(BaseModel):
    query: str
    response: str
    requisition_id: int


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """
    Invoke the main orchestration graph with intent='rag_query'.

    Useful for testing the full end-to-end RAG flow:
    API → main_graph → rag_query_node → rag_query_subgraph → LLM + tools → response
    """
    initial_state = OrchestratorState(
        intent="rag_query",
        requisition_id=request.requisition_id,
        user_id=request.user_id,
        result={"query": request.query},
    )

    try:
        final_state = await main_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Graph invocation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph execution failed: {str(e)}",
        )

    # main_graph returns a dict when invoked
    if isinstance(final_state, dict):
        error = final_state.get("error")
        result = final_state.get("result") or {}
    else:
        error = final_state.error
        result = final_state.result or {}

    if error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )

    return RAGQueryResponse(
        query=request.query,
        response=result.get("response", ""),
        requisition_id=request.requisition_id,
    )
