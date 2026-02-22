"""
Send assessment node - initiates the assessment dispatch subgraph.

This node is the ENTRY POINT for creating and sending HackerRank tests.
It validates eligibility, creates the test, and triggers Lever email delivery.

Triggered by:
- HR Manager clicks "Send Assessment" button for a specific candidate
- Candidate must be in a valid stage (not already sent, not at later stage)
"""
from ..state import OrchestratorState  # Import state schema
import logging  # For debug/info logging

# Create a logger instance for this module
# Logs will be prefixed with the module name for easy filtering
logger = logging.getLogger(__name__)


def send_assessment_node(state: OrchestratorState) -> OrchestratorState:
    """
    Initiates the assessment dispatch subgraph.
    
    This node acts as a WRAPPER around the assessment dispatch subgraph.
    It validates candidate eligibility, then creates and sends the HackerRank test.
    
    The assessment dispatch subgraph will:
    1. Validate candidate is in valid stage (not "assessment_sent", not "interview_scheduled", etc.)
    2. If invalid: Return error immediately (e.g., "Assessment already sent")
    3. Fetch candidate's full profile from DB (name, email, requisition info)
    4. Create test via HackerRank API (returns test_link and test_id)
    5. In parallel:
       - Update candidate stage in Lever to "Assessment Sent"
         (This triggers Lever's email automation which sends the test link to candidate)
       - Set up webhook listener for "assessment_completed" event
       - Update application.status in DB to "assessment_sent"
       - Store test_link and test_id in application record
    6. Wait for all parallel updates to complete
    7. Return success confirmation to HR Manager
    
    Design notes:
    - Assessment results arrive LATER via Lever webhook
    - Webhook triggers re-ranking if assessment_counter hits threshold
    - HackerRank test creation is idempotent (same candidate = same test)
    - Email delivery is handled by Lever (not by us)
    
    Args:
        state: Current orchestrator state
               REQUIRED: state.application_id must be set (which candidate to send to)
               OPTIONAL: state.user_id (which HR manager triggered this)
        
    Returns:
        Updated state with either:
        - state.result populated with test link (if successful)
        - state.error populated (if ineligible or HackerRank API failed)
    """
    # ==================== LOGGING ====================
    # Log that assessment dispatch was triggered
    logger.info(
        f"Send assessment node triggered for application_id={state.application_id}, "
        f"user_id={state.user_id}"
    )
    
    # ==================== INPUT VALIDATION ====================
    # Assessment dispatch REQUIRES application_id to know which candidate
    if not state.application_id:
        logger.error("Send assessment triggered without application_id")
        state.error = "Missing application_id for assessment dispatch"
        return state
    
    # ==================== SUBGRAPH INVOCATION ====================
    try:
        # TODO: This is where we'll invoke the assessment dispatch subgraph
        # The subgraph will validate eligibility, create HackerRank test, update Lever
        # We'll call it like: send_assessment_subgraph.invoke(assessment_state)
        
        # For now, just log what WOULD happen
        logger.info(
            f"Would invoke assessment dispatch subgraph for application {state.application_id}"
        )
        
        # ==================== PLACEHOLDER RESULT ====================
        # In production, this would return the test link
        state.result = {
            "status": "pending",
            "message": "Assessment dispatch subgraph not yet implemented",
            "application_id": state.application_id,
            "next_step": "Create HackerRank test and update Lever stage"
        }
        
    except Exception as e:
        # ==================== ERROR HANDLING ====================
        # Catch ANY exception from the subgraph
        logger.error(f"Error in send assessment node: {str(e)}", exc_info=True)
        
        # Store error message in state
        state.error = f"Assessment dispatch failed: {str(e)}"
    
    # ==================== RETURN UPDATED STATE ====================
    # Return the modified state object
    # LangGraph will pass this to the next node or END
    return state
