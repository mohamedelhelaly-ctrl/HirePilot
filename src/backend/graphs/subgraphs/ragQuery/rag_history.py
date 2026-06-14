"""
In-memory LangChain chat history for the RAG query subgraph.

Sessions are keyed by chat_thread_id (e.g. rag-{requisition_id}-{uuid}).
History lives in process memory and resets when the server restarts.
"""

import logging
import os
from threading import Lock
from typing import Optional

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)

MAX_RAG_HISTORY_MESSAGES = int(os.getenv("RAG_MAX_HISTORY_MESSAGES", "20"))

_histories: dict[str, InMemoryChatMessageHistory] = {}
_lock = Lock()


def build_default_thread_id(requisition_id: int, user_id: Optional[int] = None) -> str:
    return f"rag-req-{requisition_id}-user-{user_id or 0}"


def get_rag_history(thread_id: str) -> InMemoryChatMessageHistory:
    with _lock:
        if thread_id not in _histories:
            _histories[thread_id] = InMemoryChatMessageHistory()
            logger.info("[rag_history] created session thread_id=%s", thread_id)
        return _histories[thread_id]


def clear_rag_history(thread_id: str) -> None:
    with _lock:
        _histories.pop(thread_id, None)
    logger.info("[rag_history] cleared session thread_id=%s", thread_id)


def trim_rag_history(history: InMemoryChatMessageHistory) -> None:
    excess = len(history.messages) - MAX_RAG_HISTORY_MESSAGES
    if excess <= 0:
        return
    with _lock:
        del history.messages[:excess]
    logger.debug(
        "[rag_history] trimmed %d message(s), remaining=%d",
        excess,
        len(history.messages),
    )


def append_turn(history: InMemoryChatMessageHistory, user_text: str, assistant_text: str) -> None:
    history.add_user_message(user_text)
    history.add_ai_message(assistant_text)
    trim_rag_history(history)


def format_conversation_history(
    messages: list[BaseMessage],
    *,
    exclude_last_user: bool = True,
) -> str:
    """Render prior turns for the ReAct prompt (excludes the current question)."""
    lines: list[str] = []
    iterable = messages[:-1] if exclude_last_user and messages else messages

    for message in iterable:
        if isinstance(message, HumanMessage):
            lines.append(f"User: {message.content}")
        elif isinstance(message, AIMessage):
            lines.append(f"Assistant: {message.content}")

    if not lines:
        return ""

    return "## Prior conversation\n" + "\n".join(lines) + "\n\n"
