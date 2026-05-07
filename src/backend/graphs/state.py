"""
State schemas for the main orchestration graph.

This module defines the state object that flows through the LangGraph orchestrator.
State is immutable between nodes - each node returns a new/updated state instance.
"""


from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class OrchestratorState(BaseModel):
    """
    Main state schema for the orchestration graph.
    
    This state object is passed between ALL nodes in the main orchestrator graph.
    It carries context about what workflow to run, who triggered it, and results.
    
    LangGraph passes this state through the graph:
    Entry → Router → Specific Node → Exit
    
    Each node can read from state and return an updated state.
    """
    
    # ==================== ROUTING INFORMATION ====================
    # The 'intent' field tells the router which subgraph to invoke
    intent: Optional[Literal[
        "background_job",      # Scheduled task (e.g., 24-hour batch screening)
        "live_interview",      # Start real-time interview transcription
        "rag_query",           # Answer question about candidates
        "batch_screening"      # Score and rank all candidates for a requisition
    ]] = None 
    

    # ==================== CONTEXT IDENTIFIERS ====================
    # These IDs tell the subgraphs which entities to operate on
    requisition_id: Optional[int] = None  
    application_id: Optional[int] = None  
    user_id: Optional[int] = None         # Which HR/Hiring Manager triggered this (for auth/audit)
    session_id: Optional[str] = None      # WebSocket session ID (required for live_interview)
    

    # ==================== TRIGGER FLAGS ====================
    # If True, batch screening runs even if counter threshold isn't met, Set to True when HR clicks "Trigger Screening" button
    manual_trigger: bool = False  


    # ==================== RESULTS & ERRORS ====================
    # After a subgraph completes, it stores results/errors here
    result: Optional[Dict[str, Any]] = None 
    error: Optional[str] = None
    

    # ==================== METADATA ====================
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # When this workflow started (auto-set to current UTC time)
    next_node: Optional[str] = None  # Internal field for conditional routing (rarely used directly)
    
    class Config:
        # Allow datetime and other non-standard types in Pydantic model
        arbitrary_types_allowed = True
