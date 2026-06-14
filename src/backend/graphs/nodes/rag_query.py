"""
RAG query node — invokes the RAG query subgraph with in-memory chat history.
"""
import logging
from langchain_core.messages import HumanMessage

from ..state import OrchestratorState
from ..subgraphs.ragQuery import rag_query_subgraph
from ..subgraphs.ragQuery.rag_history import (
    append_turn,
    build_default_thread_id,
    get_rag_history,
)


logger = logging.getLogger(__name__)


async def rag_query_node(state: OrchestratorState) -> OrchestratorState:
    """
    Async wrapper that bridges OrchestratorState → RAGQueryState → result.

    Loads prior turns from LangChain in-memory history, runs the subgraph,
    then persists the new user/assistant turn back to history.
    """
    query_text = state.query if state else None
    thread_id = state.chat_thread_id or build_default_thread_id(
        state.requisition_id or 0,
        state.user_id,
    )

    logger.info(
        f"[rag_query_node] triggered query={query_text!r} requisition_id={state.requisition_id} "
        f"user_id={state.user_id} chat_thread_id={thread_id}"
    )
    logger.debug(f"[rag_query_node] incoming state={state.dict(exclude_none=True)}")

    if not query_text:
        logger.error("RAG query triggered without query text")
        return state.model_copy(update={"error": "Missing query text for RAG search"})

    if not state.requisition_id:
        logger.error("RAG query triggered without requisition_id")
        return state.model_copy(update={"error": "Missing requisition_id for RAG search"})

    try:
        history = get_rag_history(thread_id)
        prior_messages = list(history.messages)
        current_message = HumanMessage(content=query_text)
        conversation_messages = prior_messages + [current_message]

        rag_input = {
            "query": query_text,
            "requisition_id": state.requisition_id,
            "user_id": state.user_id,
            "chat_thread_id": thread_id,
            "messages": conversation_messages,
            "response": "",
        }
        logger.debug(
            f"[rag_query_node] rag_input thread_id={thread_id} "
            f"prior_turns={len(prior_messages)}"
        )

        rag_result = await rag_query_subgraph.ainvoke(rag_input)
        response_text = rag_result.get("response", "")

        logger.info(
            f"[rag_query_node] rag_query_subgraph completed response_length={len(response_text)} "
            f"error={rag_result.get('error')!r}"
        )
        logger.debug(f"[rag_query_node] rag_result={rag_result}")

        if response_text:
            append_turn(history, query_text, response_text)

        return state.model_copy(update={
            "chat_thread_id": thread_id,
            "result": {
                "query": query_text,
                "response": response_text,
                "chat_thread_id": thread_id,
            }
        })

    except Exception as e:
        logger.error(f"Error in RAG query node: {e}", exc_info=True)
        return state.model_copy(update={"error": f"RAG query failed: {str(e)}"})
