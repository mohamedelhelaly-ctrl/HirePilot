"""
Main orchestration graph.

This is the CENTRAL HUB for all AI-driven workflows in Incorta-HR.
Every LangGraph workflow starts here - it routes requests to specialized subgraphs.

Architecture:
- 1 orchestrator graph (this file)
- 6 specialized subgraphs (batch screening, assessment dispatch, scheduling, live interview, RAG, re-ranking)
- State flows from entry → router → specific node → exit
"""

# LangGraph core imports
from langgraph.graph import StateGraph, START, END  # StateGraph = graph builder, END = terminal node
from .state import OrchestratorState  # Our state schema
# Import all node functions
from .nodes import (
    router_node,
    batch_screening_node,
    webhook_handler_node,
    live_interview_node,
    schedule_interview_node,
    send_assessment_node,
    rag_query_node,
    view_candidates_node,
)
import logging  # For debug/info logging

# Create logger for this module
logger = logging.getLogger(__name__)


def create_main_graph():
    """
    Creates and compiles the main orchestration graph.
    
    This function is called ONCE at startup to build the graph structure.
    The compiled graph is reused across all requests (stateless execution).
    
    Graph structure:
    ┌─────────┐
    │  START  │
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ router  │ ◄── Entry point (reads intent from state)
    └────┬────┘
         │
         ├─────► batch_screening ──► END
         ├─────► webhook_handler ──► ... (TODO)
         ├─────► live_interview ──► ... (TODO)
         ├─────► schedule_interview ──► ... (TODO)
         ├─────► send_assessment ──► ... (TODO)
         ├─────► rag_query ──► ... (TODO)
         ├─────► view_candidates ──► ... (TODO)
         └─────► END (if no valid intent)
    
    The graph routes incoming requests to appropriate subgraphs based on intent:
    - background_job → Batch Screening Subgraph
    - webhook_event → Webhook handler (routes to various subgraphs)
    - live_interview → Live Interview Subgraph
    - schedule_interview → Interview Scheduling Subgraph
    - send_assessment → Assessment Dispatch Subgraph
    - rag_query → RAG Query Subgraph
    - view_candidates → Simple DB read (no subgraph)
    
    Returns:
        Compiled StateGraph ready for execution via graph.invoke(state)
    """
    
    # ==================== GRAPH INITIALIZATION ====================
    # Create a new StateGraph instance with our state schema
    # This tells LangGraph what shape of data flows through the graph
    workflow = StateGraph(OrchestratorState)
    
    # ==================== ADD NODES ====================
    # router_node is NOT registered as a graph node — it is a pure routing
    # function (returns a string, not a state update) used as the conditional
    # edge function from START.  Registering it as a node would cause
    # LangGraph to raise "Expected dict, got <route_string>".
    
    # Batch screening node - scores and ranks all candidates for a requisition
    # Invoked when intent="batch_screening" or intent="background_job"
    workflow.add_node("batch_screening", batch_screening_node)
    
    # Webhook handler node - processes Lever webhook events and routes to actions
    # Invoked when intent="webhook_event"
    workflow.add_node("webhook_handler", webhook_handler_node)
    
    # Live interview node - real-time transcription and copilot assistance
    # Invoked when intent="live_interview"
    workflow.add_node("live_interview", live_interview_node)
    
    # Schedule interview node - find calendar slots and create events
    # Invoked when intent="schedule_interview"
    workflow.add_node("schedule_interview", schedule_interview_node)
    
    # Send assessment node - create and dispatch HackerRank tests
    # Invoked when intent="send_assessment"
    workflow.add_node("send_assessment", send_assessment_node)
    
    # RAG query node - semantic search and LLM-powered Q&A about candidates
    # Invoked when intent="rag_query"
    workflow.add_node("rag_query", rag_query_node)
    
    # View candidates node - simple DB read of ranked candidate list
    # Invoked when intent="view_candidates"
    workflow.add_node("view_candidates", view_candidates_node)
    
    # ==================== ROUTING FROM START ====================
    # router_node is a plain function that reads state.intent and returns a
    # string key.  It acts as the conditional edge from the graph entry point.
    workflow.add_conditional_edges(
        START,
        router_node,
        {
            "batch_screening":   "batch_screening",
            "webhook_handler":   "webhook_handler",
            "live_interview":    "live_interview",
            "schedule_interview":"schedule_interview",
            "send_assessment":   "send_assessment",
            "rag_query":         "rag_query",
            "view_candidates":   "view_candidates",
            "end": END,
        },
    )
    
    # STATIC EDGES from all nodes to END
    # After each workflow completes, end the graph
    # In the future, we might add post-processing nodes here:
    # - Sync results to Lever
    # - Push WebSocket updates to frontend
    # - Trigger re-ranking if needed
    workflow.add_edge("batch_screening", END)
    workflow.add_edge("webhook_handler", END)
    workflow.add_edge("live_interview", END)
    workflow.add_edge("schedule_interview", END)
    workflow.add_edge("send_assessment", END)
    workflow.add_edge("rag_query", END)
    workflow.add_edge("view_candidates", END)
    
    # ==================== COMPILE THE GRAPH ====================
    # Compilation validates the graph structure and optimizes execution
    # The compiled graph is immutable and can be reused across requests
    graph = workflow.compile()
    
    # Log success for monitoring
    logger.info("Main orchestration graph compiled successfully")
    
    # Return the compiled graph
    return graph


# ==================== SINGLETON INSTANCE ====================
# Create the graph once at module import time
# This graph instance is reused for all requests (graph is stateless)
# Each request creates a NEW state object and passes it to graph.invoke(state)
main_graph = create_main_graph()
