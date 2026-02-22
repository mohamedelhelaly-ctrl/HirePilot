"""
State schemas for the main orchestration graph.

This module defines the state object that flows through the LangGraph orchestrator.
State is immutable between nodes - each node returns a new/updated state instance.
"""

# Type hints for better IDE support and validation
from typing import Optional, Dict, Any, List, Literal
# Pydantic for runtime validation and schema definition
from pydantic import BaseModel, Field
# For tracking when workflows are triggered
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
    # This is set by the API endpoint or webhook handler before invoking the graph
    intent: Optional[Literal[
        "background_job",      # Scheduled task (e.g., 24-hour batch screening)
        "webhook_event",       # Lever webhook received (new candidate, assessment, etc.)
        "live_interview",      # Start real-time interview transcription
        "schedule_interview",  # Create calendar event for interview
        "send_assessment",     # Dispatch HackerRank test to candidate
        "rag_query",           # Answer question about candidates
        "view_candidates",     # Fetch ranked candidate list (no LLM, just DB read)
        "batch_screening"      # Score and rank all candidates for a requisition
    ]] = None  # None means no intent specified → router will end immediately
    
    # ==================== CONTEXT IDENTIFIERS ====================
    # These IDs tell the subgraphs which entities to operate on
    
    requisition_id: Optional[int] = None  # Which job opening (required for batch_screening, view_candidates)
    application_id: Optional[int] = None  # Which specific candidate application (required for send_assessment, schedule_interview)
    user_id: Optional[int] = None         # Which HR/Hiring Manager triggered this (for auth/audit)
    session_id: Optional[str] = None      # WebSocket session ID (required for live_interview)
    
    # ==================== WEBHOOK CONTEXT ====================
    # When a Lever webhook triggers the graph, we store the raw event here
    
    webhook_event_type: Optional[str] = None  # e.g., "candidate_stage_change", "assessment_completed"
    webhook_payload: Optional[Dict[str, Any]] = None  # Full JSON payload from Lever
    
    # ==================== TRIGGER FLAGS ====================
    # Flags that modify subgraph behavior
    
    manual_trigger: bool = False  # If True, batch screening runs even if counter threshold isn't met
                                   # Set to True when HR clicks "Trigger Screening" button
    
    # ==================== RESULTS & ERRORS ====================
    # After a subgraph completes, it stores results/errors here
    
    result: Optional[Dict[str, Any]] = None  # Success result from subgraph (e.g., {"candidates_scored": 15})
    error: Optional[str] = None               # Error message if subgraph failed
    
    # ==================== METADATA ====================
    # Tracking and debugging information
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # When this workflow started (auto-set to current UTC time)
    next_node: Optional[str] = None  # Internal field for conditional routing (rarely used directly)
    
    class Config:
        # Allow datetime and other non-standard types in Pydantic model
        arbitrary_types_allowed = True
