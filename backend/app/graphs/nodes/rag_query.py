"""
RAG query node — invokes the RAG query subgraph.
"""
import logging
from langchain_core.messages import HumanMessage

from ..state import OrchestratorState
from ..subgraphs.rag_query.graph import rag_query_subgraph

logger = logging.getLogger(__name__)


async def rag_query_node(state: OrchestratorState) -> OrchestratorState:
    """
    Async wrapper that bridges OrchestratorState → RAGQueryState → result.

    Expects state.result to contain {"query": "<user question>"}.
    Writes the LLM answer back to state.result["response"].
    """
    query_text = state.result.get("query") if state.result else None
    logger.info(f"RAG query node triggered: query='{query_text}', requisition_id={state.requisition_id}")

    if not query_text:
        logger.error("RAG query triggered without query text")
        return state.model_copy(update={"error": "Missing query text for RAG search"})

    try:
        rag_input = {
            "query": query_text,
            "requisition_id": state.requisition_id,
            "user_id": state.user_id,
            "messages": [HumanMessage(content=query_text)],
            "response": "",
        }

        rag_result = await rag_query_subgraph.ainvoke(rag_input)

        return state.model_copy(update={
            "result": {
                "query": query_text,
                "response": rag_result.get("response", ""),
            }
        })

    except Exception as e:
        logger.error(f"Error in RAG query node: {e}", exc_info=True)
        return state.model_copy(update={"error": f"RAG query failed: {str(e)}"})
