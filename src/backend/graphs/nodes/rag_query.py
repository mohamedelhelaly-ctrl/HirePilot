"""
RAG query node — invokes the RAG query subgraph with persistent chat history.
"""
import logging
from langchain_core.messages import HumanMessage

from ..state import OrchestratorState
from ..subgraphs.ragQuery import rag_query_subgraph
from ..subgraphs.ragQuery.rag_history import RAGSummaryBufferMemory, format_conversation_history
from models.database import AsyncSessionLocal
from controllers.ChatController import ChatController


logger = logging.getLogger(__name__)
chat_controller = ChatController()


async def rag_query_node(state: OrchestratorState) -> OrchestratorState:
    """
    Async wrapper that bridges OrchestratorState → RAGQueryState → result.

    Loads prior turns from the database, runs the subgraph,
    then persists the new user/assistant turn.
    """
    query_text = state.query if state else None

    logger.info(
        f"[rag_query_node] triggered query={query_text!r} requisition_id={state.requisition_id} "
        f"user_id={state.user_id} chat_thread_id={state.chat_thread_id}"
    )
    logger.debug(f"[rag_query_node] incoming state={state.dict(exclude_none=True)}")

    if not query_text:
        logger.error("RAG query triggered without query text")
        return state.model_copy(update={"error": "Missing query text for RAG search"})

    if not state.requisition_id:
        logger.error("RAG query triggered without requisition_id")
        return state.model_copy(update={"error": "Missing requisition_id for RAG search"})

    try:
        async with AsyncSessionLocal() as db:
            thread = await chat_controller.ensure_thread_for_rag(
                db,
                state.chat_thread_id,
                state.requisition_id,
                state.user_id,
            )
            thread_id = thread.external_id

            summary, prior_messages = await RAGSummaryBufferMemory.load_prompt_context(
                db, thread_id
            )
            current_message = HumanMessage(content=query_text)
            conversation_messages = prior_messages + [current_message]

            rag_input = {
                "query": query_text,
                "requisition_id": state.requisition_id,
                "user_id": state.user_id,
                "chat_thread_id": thread_id,
                "conversation_summary": summary,
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
                await chat_controller.set_title_from_first_message(
                    db, thread.id, query_text
                )
                await RAGSummaryBufferMemory.append_turn(
                    db, thread_id, query_text, response_text
                )

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
