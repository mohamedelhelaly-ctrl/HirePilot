from langgraph.graph import StateGraph, START, END  # StateGraph = graph builder, END = terminal node
from .state import OrchestratorState  # Our state schema

# Import all node functions
from .nodes import (
    router_node,
    batch_screening_node,
    # live_interview_node,
    # rag_query_node,
)
import logging 

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
         ├─────► live_interview ──► END
         ├─────► rag_query ──► END
         └─────► END (if no valid intent)
    
    The graph routes incoming requests to appropriate subgraphs based on intent:
    - background_job → Batch Screening Subgraph
    - live_interview → Live Interview Subgraph
    - rag_query → RAG Query Subgraph
    
    Returns:
        Compiled StateGraph ready for execution via graph.invoke(state)
    """
    
    workflow = StateGraph(OrchestratorState)
    
    # ==================== ADD NODES ====================
    # router_node is NOT registered as a graph node — it is a pure routing
    
    # Batch screening node - scores and ranks all candidates for a requisition
    # Invoked when intent="batch_screening" or intent="background_job"
    workflow.add_node("batch_screening", batch_screening_node)
    
    # Live interview node - real-time transcription and copilot assistance
    # Invoked when intent="live_interview"
    # workflow.add_node("live_interview", live_interview_node)
    
    # RAG query node - semantic search and LLM-powered Q&A about candidates
    # Invoked when intent="rag_query"
    # workflow.add_node("rag_query", rag_query_node)
    
    # ==================== ROUTING FROM START ====================
    # router_node is a plain function that reads state.intent and returns a
    # string key.  It acts as the conditional edge from the graph entry point.
    workflow.add_conditional_edges(
        START,
        router_node,
        {
            "batch_screening":   "batch_screening",
            # "live_interview":    "live_interview",
            # "rag_query":         "rag_query",
            "end": END,
        },
    )
    
    # STATIC EDGES from all nodes to END
    workflow.add_edge("batch_screening", END)
    # workflow.add_edge("live_interview", END)
    # workflow.add_edge("rag_query", END)

    
    # ==================== COMPILE THE GRAPH ====================
    graph = workflow.compile()
    
    # Log success for monitoring
    logger.info("Main orchestration graph compiled successfully")
    
    # Return the compiled graph
    return graph


# ==================== SINGLETON INSTANCE ====================
main_graph = create_main_graph()