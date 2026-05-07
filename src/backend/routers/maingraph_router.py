"""
Universal Graph Executor Router

Generic endpoint to dynamically invoke the main LangGraph orchestrator
with any supported intent.

This replaces the need for hard-coded endpoints per workflow.

POST /api/graph/execute
    - Accepts intent + optional requisition_id + optional user_id + optional payload
    - Builds OrchestratorState
    - Invokes main_graph.ainvoke()
    - Returns result or error

"""

import logging
from fastapi import APIRouter, HTTPException, status

from graphs import main_graph, OrchestratorState
from models.schemas import GraphExecuteResponse, GraphExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter()

# Supported intents
SUPPORTED_INTENTS = {
    "batch_screening",
    "live_interview",
    "rag_query",
}



@router.post(
    "/execute",
    response_model=GraphExecuteResponse,
    summary="Execute main orchestration graph with dynamic intent",
    status_code=status.HTTP_200_OK,
)
async def execute_graph(request: GraphExecuteRequest):
    """
    Dynamically invoke the main LangGraph orchestrator with specified intent.

    This is a universal endpoint that replaces hard-coded endpoints per workflow.
    The main_graph routes the request to the appropriate subgraph based on intent.

    Request Example:
        ```json
        {
            "intent": "batch_screening",
            "requisition_id": 42,
            "user_id": 1,
            "payload": {"manual_trigger": true}
        }
        ```

    Response Example (success):
        ```json
        {
            "intent": "batch_screening",
            "result": {
                "candidates_scored": 15,
                "candidates_saved": 12,
                "top_candidate": {...}
            },
            "error": null
        }
        ```

    Response Example (error):
        ```json
        {
            "intent": "batch_screening",
            "result": null,
            "error": "Requisition 42 not found"
        }
        ```

    Returns:
        GraphExecuteResponse with result dict or error string
        
    Raises:
        HTTPException 400: If intent is not supported
        HTTPException 500: If graph execution raises unexpected error
    """

    # 1. Validate intent
    if request.intent not in SUPPORTED_INTENTS:
        logger.warning(
            f"[graph/execute] Invalid intent: {request.intent}. "
            f"Supported: {SUPPORTED_INTENTS}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported intent '{request.intent}'. "
                f"Supported intents: {', '.join(sorted(SUPPORTED_INTENTS))}"
            ),
        )

    logger.info(
        f"[graph/execute] Executing intent='{request.intent}' "
        f"with requisition_id={request.requisition_id}, "
        f"user_id={request.user_id}"
    )

    # 2. Build orchestrator state
    graph_state = OrchestratorState(
        intent=request.intent,
        requisition_id=request.requisition_id,
        user_id=request.user_id,
        result=request.payload or {},
    )

    # 3. Invoke the graph
    try:
        raw_state = await main_graph.ainvoke(graph_state)
        
        # Handle both OrchestratorState and dict return types
        if isinstance(raw_state, OrchestratorState):
            final_state = raw_state
        else:
            final_state = OrchestratorState(**raw_state)

    except Exception as exc:
        logger.error(
            f"[graph/execute] Graph invocation failed for intent='{request.intent}': {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph execution failed: {str(exc)}",
        )

    # 4. Extract result and error
    error_message = final_state.error if final_state.error else None
    result_data = final_state.result if final_state.result else None

    if error_message:
        logger.warning(
            f"[graph/execute] Graph returned error for intent='{request.intent}': "
            f"{error_message}"
        )

    # 5. Return response
    return GraphExecuteResponse(
        intent=request.intent,
        result=result_data,
        error=error_message,
    )
