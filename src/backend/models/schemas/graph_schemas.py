from pydantic import BaseModel, Field
from typing import Optional, Any, Literal

# Graph Executor schemas
class GraphExecuteRequest(BaseModel):
    """
    Request to execute the main orchestration graph.

    Fields mirror the input section of OrchestratorState so the router
    can forward them directly into the graph without any transformation.

    Args:
        intent: Which workflow to invoke. Must be one of the recognised
            intent literals used by the orchestrator router.
        requisition_id: Requisition context (required for batch_screening /
            rag_query workflows).
        query: Free-text question for the rag_query workflow.
        user_id: HR / Hiring-manager who triggered the workflow (used for
            auth and audit logging).
        application_id: Specific application to operate on (optional; used
            by subgraphs that target a single candidate).
        session_id: WebSocket session ID — required for live_interview so
            the subgraph knows which socket to stream results to.
        manual_trigger: When True, batch screening runs immediately even if
            the counter threshold has not been reached (e.g. HR presses
            "Trigger Screening" in the UI).
    """
    intent: Literal[
        "background_job",
        "live_interview",
        "rag_query",
        "batch_screening",
    ] = Field(
        ...,
        description="Workflow intent to execute",
        examples=["batch_screening", "rag_query", "live_interview"],
    )
    requisition_id: Optional[int] = Field(
        None,
        description="Requisition ID for context (required for batch_screening / rag_query)",
    )
    query: Optional[str] = Field(
        None,
        description="Free-text question passed to the rag_query workflow",
    )
    user_id: Optional[int] = Field(
        None,
        description="HR / Hiring-manager user ID for auth and audit (if applicable)",
    )
    application_id: Optional[int] = Field(
        None,
        description="Specific application ID for subgraphs that target a single candidate",
    )
    session_id: Optional[str] = Field(
        None,
        description="WebSocket session ID — required for live_interview workflow",
    )
    manual_trigger: bool = Field(
        False,
        description="Force batch screening to run regardless of counter threshold",
    )


class GraphExecuteResponse(BaseModel):
    """
    Response from graph execution.

    Fields mirror the output section of OrchestratorState.
    """
    intent: str
    result: Optional[dict[str, Any]] = None
    response: Optional[str] = None
    saved_count: Optional[int] = None
    updated_count: Optional[int] = None
    error: Optional[str] = None