"""
Router node - determines which subgraph to invoke based on the intent.

This is the FIRST node executed in every workflow.
It reads the 'intent' from state and returns the name of the next node.
LangGraph uses this return value to route execution to the correct subgraph.
"""
from typing import Literal  # For type-safe string literals
from ..state import OrchestratorState  # Import state schema from parent directory


def router_node(state: OrchestratorState) -> Literal[
    "batch_screening",     # Route to batch screening subgraph
    "webhook_handler",     # Route to webhook processing node
    "live_interview",      # Route to live interview subgraph
    "schedule_interview",  # Route to interview scheduling subgraph
    "send_assessment",     # Route to assessment dispatch subgraph
    "rag_query",           # Route to RAG query subgraph
    "view_candidates",     # Route to simple DB read node
    "end"                  # End the workflow (no subgraph to invoke)
]:
    """
    Routes the workflow to the appropriate subgraph based on the intent.
    
    This function is called by LangGraph as a conditional edge.
    It doesn't modify state - it just decides where to route next.
    
    Flow:
    1. Read intent from state
    2. Look up which node should handle that intent
    3. Return the node name (LangGraph routes execution there)
    
    Args:
        state: Current orchestrator state containing the intent
        
    Returns:
        String name of the next node to execute (must match a node in the graph)
    """
    # Extract the intent field from state
    # Intent tells us what kind of workflow to run
    intent = state.intent
    
    # Safety check: if no intent was set, we can't route anywhere
    if not intent:
        # No intent specified, end immediately
        # This prevents the graph from running when state is malformed
        return "end"
    
    # ==================== ROUTING LOGIC ====================
    # Map each possible intent value to its corresponding node name
    # This is the single source of truth for routing decisions
    routing_map = {
        # Direct intents - one-to-one mapping
        "batch_screening": "batch_screening",        # Manual or threshold-triggered screening
        "webhook_event": "webhook_handler",          # Lever webhook received (needs further routing)
        "live_interview": "live_interview",          # Start interview copilot WebSocket
        "schedule_interview": "schedule_interview",  # Find slots and create calendar event
        "send_assessment": "send_assessment",        # Create HackerRank test
        "rag_query": "rag_query",                    # Search candidates and answer question
        "view_candidates": "view_candidates",        # Just fetch pre-computed rankings
        
        # Aliased intent - background jobs currently only trigger batch screening
        "background_job": "batch_screening",  # APScheduler triggers → batch screening subgraph
    }
    
    # Look up the intent in our routing map
    # If intent is not in map, default to "end" (graceful failure)
    next_node = routing_map.get(intent, "end")
    
    # Return the node name - LangGraph will invoke that node next
    return next_node
