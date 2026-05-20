"""
RAG query node — invokes the RAG query subgraph.
"""
import logging
from langchain_core.messages import HumanMessage

from ..state import OrchestratorState
from ..subgraphs.ragQuery import rag_query_subgraph


logger = logging.getLogger(__name__)


async def rag_query_node(state: OrchestratorState) -> OrchestratorState:
    """
    Async wrapper that bridges OrchestratorState → RAGQueryState → result.

    Expects state.result to contain {"query": "<user question>"}.
    Writes the LLM answer back to state.result["response"].
    """
    query_text = state.query if state else None
    logger.info(
        f"[rag_query_node] triggered query={query_text!r} requisition_id={state.requisition_id} "
        f"user_id={state.user_id} application_id={state.application_id} session_id={state.session_id}"
    )
    logger.debug(f"[rag_query_node] incoming state={state.dict(exclude_none=True)}")

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
        logger.debug(f"[rag_query_node] rag_input={rag_input}")

        rag_result = await rag_query_subgraph.ainvoke(rag_input)
        logger.info(
            f"[rag_query_node] rag_query_subgraph completed response_length={len(rag_result.get('response',''))} "
            f"error={rag_result.get('error')!r}"
        )
        logger.debug(f"[rag_query_node] rag_result={rag_result}")

        return state.model_copy(update={
            "result": {
                "query": query_text,
                "response": rag_result.get("response", ""),
            }
        })

    except Exception as e:
        logger.error(f"Error in RAG query node: {e}", exc_info=True)
        return state.model_copy(update={"error": f"RAG query failed: {str(e)}"})
