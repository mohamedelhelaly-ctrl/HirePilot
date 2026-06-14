"""
Persistent LangChain-compatible chat history for the RAG query subgraph.

Messages are stored in PostgreSQL (chat_threads / chat_messages).
Long conversations use a ConversationSummaryBuffer-style pattern: older turns
are summarized into chat_threads.summary; recent turns stay verbatim.
"""

import asyncio
import logging
import os
from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from models.crud.chat_crud import (
    append_chat_message,
    get_messages_by_thread,
    get_thread_by_external_id,
    update_thread_summary,
)
from models.tables_enums import ChatMessageRole

logger = logging.getLogger(__name__)

RAG_MEMORY_BUFFER_MESSAGES = int(os.getenv("RAG_MEMORY_BUFFER_MESSAGES", "6"))
RAG_MEMORY_SUMMARY_THRESHOLD = int(os.getenv("RAG_MEMORY_SUMMARY_THRESHOLD", "12"))


def _db_messages_to_langchain(messages) -> List[BaseMessage]:
    lc: List[BaseMessage] = []
    for msg in messages:
        if msg.role == ChatMessageRole.USER:
            lc.append(HumanMessage(content=msg.content))
        else:
            lc.append(AIMessage(content=msg.content))
    return lc


def format_conversation_history(
    messages: list[BaseMessage],
    *,
    summary: Optional[str] = None,
    exclude_last_user: bool = True,
) -> str:
    """Render prior turns (+ optional summary) for the ReAct prompt."""
    parts: list[str] = []

    if summary:
        parts.append("## Conversation summary")
        parts.append(summary.strip())
        parts.append("")

    lines: list[str] = []
    iterable = messages[:-1] if exclude_last_user and messages else messages

    for message in iterable:
        if isinstance(message, HumanMessage):
            lines.append(f"User: {message.content}")
        elif isinstance(message, AIMessage):
            lines.append(f"Assistant: {message.content}")

    if lines:
        parts.append("## Recent messages")
        parts.extend(lines)
        parts.append("")

    if not parts:
        return ""

    return "\n".join(parts)


def _build_summarization_prompt(existing_summary: Optional[str], messages) -> str:
    lines = []
    if existing_summary:
        lines.append(f"Existing summary:\n{existing_summary}\n")
    lines.append("Conversation to summarize:")
    for msg in messages:
        role = "User" if msg.role == ChatMessageRole.USER else "Assistant"
        lines.append(f"{role}: {msg.content}")
    lines.append(
        "\nWrite a concise summary capturing key facts: candidate names, IDs, "
        "scores, skills, and decisions discussed. Keep it under 400 words."
    )
    return "\n".join(lines)


async def _summarize_messages(
    existing_summary: Optional[str],
    messages,
) -> str:
    from stores.llm.llm_config import llm_rag

    prompt = _build_summarization_prompt(existing_summary, messages)
    raw = await asyncio.to_thread(llm_rag.generate, prompt)
    return raw["results"][0]["generated_text"].strip()


class RAGSummaryBufferMemory:
    """ConversationSummaryBufferMemory-style helper backed by PostgreSQL."""

    @staticmethod
    async def load_prompt_context(
        db: AsyncSession,
        external_id: str,
    ) -> Tuple[Optional[str], List[BaseMessage]]:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            return None, []

        db_messages = await get_messages_by_thread(db, thread.id)
        total = len(db_messages)

        if total <= RAG_MEMORY_BUFFER_MESSAGES:
            return thread.summary, _db_messages_to_langchain(db_messages)

        if total <= RAG_MEMORY_SUMMARY_THRESHOLD:
            return thread.summary, _db_messages_to_langchain(db_messages)

        buffer_count = RAG_MEMORY_BUFFER_MESSAGES
        recent = db_messages[-buffer_count:]
        return thread.summary, _db_messages_to_langchain(recent)

    @staticmethod
    async def maybe_update_summary(db: AsyncSession, external_id: str) -> None:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            return

        db_messages = await get_messages_by_thread(db, thread.id)
        total = len(db_messages)
        if total <= RAG_MEMORY_SUMMARY_THRESHOLD:
            return

        buffer_count = RAG_MEMORY_BUFFER_MESSAGES
        to_summarize = db_messages[: total - buffer_count]
        if not to_summarize:
            return

        try:
            new_summary = await _summarize_messages(thread.summary, to_summarize)
            await update_thread_summary(db, thread.id, new_summary)
            logger.info(
                "[rag_history] updated summary thread=%s summarized=%d messages",
                external_id,
                len(to_summarize),
            )
        except Exception:
            logger.exception("[rag_history] failed to summarize thread=%s", external_id)

    @staticmethod
    async def append_turn(
        db: AsyncSession,
        external_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            logger.warning("[rag_history] append_turn unknown thread=%s", external_id)
            return

        await append_chat_message(db, thread.id, ChatMessageRole.USER, user_text)
        await append_chat_message(db, thread.id, ChatMessageRole.ASSISTANT, assistant_text)
        await RAGSummaryBufferMemory.maybe_update_summary(db, external_id)
