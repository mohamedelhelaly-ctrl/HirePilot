import logging
from langgraph.graph import StateGraph, END


from .ragQuery_state import RAGQueryState
from .ragQuery_nodes.llm_node import make_llm_node
from .rag_tools import build_rag_tools
from .prompt import build_rag_prompt

logger = logging.getLogger(__name__)


# Create the LLM node instance
_llm_node = make_llm_node(build_rag_tools, build_rag_prompt)


# ── Graph builder ─────────────────────────────────────────────────────────────

def create_rag_query_subgraph():
    """
    Build and compile the RAG query LangGraph subgraph.
    
    Uses agent architecture with single LLM node and tool-calling loop.
    
    Returns:
        CompiledStateGraph — ready to call via .invoke() or .ainvoke()
    """
    workflow = StateGraph(RAGQueryState)
    
    # Register the LLM node
    workflow.add_node("llm_node", _llm_node)
    
    # Entry point
    workflow.set_entry_point("llm_node")
    
    # The node handles its own logic and returns to END
    workflow.add_edge("llm_node", END)
    
    return workflow.compile()


# ── Compiled singleton ────────────────────────────────────────────────────────

rag_query_subgraph = create_rag_query_subgraph()

logger.info("RAG Query subgraph compiled successfully")
