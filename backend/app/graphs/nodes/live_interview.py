"""
Live interview node - initiates the live interview copilot subgraph.

This node is the ENTRY POINT for real-time interview transcription and assistance.
It validates inputs, then starts the cyclic interview loop.

Triggered by:
- HR or Hiring Manager clicks "Start Interview" button in dashboard
- WebSocket connection established for bidirectional audio/transcript streaming
"""
from ..state import OrchestratorState  # Import state schema
import logging  # For debug/info logging

# Create a logger instance for this module
# Logs will be prefixed with the module name for easy filtering
logger = logging.getLogger(__name__)


def live_interview_node(state: OrchestratorState) -> OrchestratorState:
    """
    Initiates the live interview copilot subgraph.
    
    This node acts as a WRAPPER around the live interview subgraph.
    It validates session context, then starts the real-time transcription loop.
    
    The live interview subgraph will:
    1. Fetch interview context (candidate CV, assessment score, job description, pre-generated questions)
    2. Initialize WebSocket session with session_id
    3. Create interview_session record in DB with status='in_progress'
    4. Display pre-generated questions to interviewer
    5. ENTER CYCLIC LOOP:
       - Receive audio chunk from browser via WebSocket
       - Send to Whisper for transcription
       - Append transcript chunk to DB
       - Check if 30 seconds elapsed since last analysis
       - If yes: Send transcript to LLM, generate follow-up question, push to interviewer
       - If no: Continue receiving audio (loop back)
    6. When interviewer clicks "End Interview":
       - Exit loop
       - Retrieve full transcript from DB
       - Generate post-interview summary with LLM
       - Store summary and scores
       - Increment interview counter on requisition
       - Post summary to Lever as a note
       - Check if re-ranking threshold met
    
    Design notes:
    - This is a CYCLIC GRAPH (loops until "end" message received)
    - WebSocket disconnects are handled gracefully (chunks already persisted)
    - LLM failures for follow-up questions are skipped silently
    - Transcription continues even if analysis fails
    
    Args:
        state: Current orchestrator state
               REQUIRED: state.session_id must be set (WebSocket session identifier)
               REQUIRED: state.application_id must be set (which candidate is being interviewed)
        
    Returns:
        Updated state with either:
        - state.result populated with interview summary (if successful)
        - state.error populated (if validation failed or subgraph crashed)
    """
    # ==================== LOGGING ====================
    # Log that interview copilot was triggered
    logger.info(
        f"Live interview node triggered for session_id={state.session_id}, "
        f"application_id={state.application_id}"
    )
    
    # ==================== INPUT VALIDATION ====================
    # Live interview REQUIRES both session_id (for WebSocket) and application_id (for context)
    if not state.session_id:
        logger.error("Live interview triggered without session_id")
        state.error = "Missing session_id for live interview"
        return state
    
    if not state.application_id:
        logger.error("Live interview triggered without application_id")
        state.error = "Missing application_id for live interview"
        return state
    
    # ==================== SUBGRAPH INVOCATION ====================
    try:
        # TODO: This is where we'll invoke the live interview subgraph
        # The subgraph will be a CYCLIC StateGraph with a loop for audio processing
        # We'll call it like: live_interview_subgraph.invoke(interview_state)
        
        # For now, just log what WOULD happen
        logger.info(
            f"Would start live interview subgraph for session {state.session_id}, "
            f"application {state.application_id}"
        )
        
        # ==================== PLACEHOLDER RESULT ====================
        # In production, this would return the interview summary after completion
        state.result = {
            "status": "pending",
            "message": "Live interview subgraph not yet implemented",
            "session_id": state.session_id,
            "application_id": state.application_id,
            "websocket_endpoint": f"/ws/interview/{state.session_id}"
        }
        
    except Exception as e:
        # ==================== ERROR HANDLING ====================
        # Catch ANY exception from the subgraph
        logger.error(f"Error in live interview node: {str(e)}", exc_info=True)
        
        # Store error message in state
        state.error = f"Live interview failed: {str(e)}"
    
    # ==================== RETURN UPDATED STATE ====================
    # Return the modified state object
    # LangGraph will pass this to the next node or END
    return state
