"""
Schedule interview node - initiates the interview scheduling subgraph.

This node is the ENTRY POINT for finding calendar slots and creating interview events.
It includes human-in-the-loop for HR to select time slots.

Triggered by:
- HR Manager clicks "Schedule Interview" button for a candidate
- Requires candidate availability and interviewer calendar access
"""
from ..state import OrchestratorState  # Import state schema
import logging  # For debug/info logging

# Create a logger instance for this module
# Logs will be prefixed with the module name for easy filtering
logger = logging.getLogger(__name__)


def schedule_interview_node(state: OrchestratorState) -> OrchestratorState:
    """
    Initiates the interview scheduling subgraph.
    
    This node acts as a WRAPPER around the scheduling subgraph.
    It validates inputs, then starts the human-in-the-loop scheduling flow.
    
    The interview scheduling subgraph will:
    1. Fetch candidate's stated availability from DB
    2. Check assigned interviewer's Google Calendar for free slots
    3. Find overlapping time slots (candidate availability ∩ interviewer free slots)
    4. If no slots: Suggest alternatives and INTERRUPT (wait for HR input)
    5. If slots found: Present them to HR and INTERRUPT (wait for HR selection)
    6. GRAPH RESUMES when HR submits selection
    7. Fetch candidate CV, assessment data, and job description
    8. Generate tailored interview questions using LLM (based on CV + job + interview type)
    9. In parallel:
       - Create Google Calendar event with Meet link
       - Store interview_session in DB with questions and calendar_event_id
       - Update candidate stage in Lever
    10. Send calendar invites to candidate and interviewer
    11. Return meeting details and confirmation
    
    Design notes:
    - Uses LangGraph interrupt() for human-in-the-loop
    - Questions are tailored to interview type (HR screen vs. technical)
    - Calendar event description includes questions + CV link
    - If calendar creation fails, DB transaction rolls back
    
    Args:
        state: Current orchestrator state
               REQUIRED: state.application_id must be set (which candidate to interview)
               OPTIONAL: state.user_id (which HR manager triggered this)
        
    Returns:
        Updated state with either:
        - state.result populated with meeting details (if successful)
        - state.error populated (if validation failed or slots unavailable)
    """
    # ==================== LOGGING ====================
    # Log that scheduling was triggered
    logger.info(
        f"Schedule interview node triggered for application_id={state.application_id}, "
        f"user_id={state.user_id}"
    )
    
    # ==================== INPUT VALIDATION ====================
    # Scheduling REQUIRES application_id to know which candidate
    if not state.application_id:
        logger.error("Schedule interview triggered without application_id")
        state.error = "Missing application_id for interview scheduling"
        return state
    
    # ==================== SUBGRAPH INVOCATION ====================
    try:
        # TODO: This is where we'll invoke the interview scheduling subgraph
        # The subgraph will use interrupt() to pause for HR input
        # We'll call it like: schedule_interview_subgraph.invoke(schedule_state)
        
        # For now, just log what WOULD happen
        logger.info(
            f"Would invoke interview scheduling subgraph for application {state.application_id}"
        )
        
        # ==================== PLACEHOLDER RESULT ====================
        # In production, this would return the calendar event details
        state.result = {
            "status": "pending",
            "message": "Interview scheduling subgraph not yet implemented",
            "application_id": state.application_id,
            "next_step": "Find available slots and await HR selection"
        }
        
    except Exception as e:
        # ==================== ERROR HANDLING ====================
        # Catch ANY exception from the subgraph
        logger.error(f"Error in schedule interview node: {str(e)}", exc_info=True)
        
        # Store error message in state
        state.error = f"Interview scheduling failed: {str(e)}"
    
    # ==================== RETURN UPDATED STATE ====================
    # Return the modified state object
    # LangGraph will pass this to the next node or END
    return state
