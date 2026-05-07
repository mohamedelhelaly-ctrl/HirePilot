from pydantic import BaseModel, Field
from typing import Optional, Any

# Graph Executor schemas
class GraphExecuteRequest(BaseModel):
    """
    Request to execute the main orchestration graph.
    
    Args:
        intent: Which workflow to invoke (batch_screening, rag_query, etc.)
        requisition_id: Optional requisition context
        user_id: Optional user context
        payload: Optional additional data to pass to the workflow
    """
    intent: str = Field(
        ...,
        description="Workflow intent to execute",
        examples=["batch_screening", "rag_query", "live_interview"],
    )
    requisition_id: Optional[int] = Field(
        None,
        description="Requisition ID for context (if applicable)"
    )
    user_id: Optional[int] = Field(
        None,
        description="User ID for context (if applicable)"
    )
    payload: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional data to pass to the workflow"
    )


class GraphExecuteResponse(BaseModel):
    """Response from graph execution."""
    intent: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None