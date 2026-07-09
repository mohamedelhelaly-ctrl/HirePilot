"""
LLM node for the RAG query agent — ReAct (Reason + Act) text-parsing loop.

Why not bind_tools / native tool-calling?
  Small local models (3B params, qwen2.5:3b-instruct) are unreliable at emitting
  well-formed JSON function-call payloads. bind_tools silently produces no tool
  calls or malformed ones, so the agent never retrieves real data.

This implementation instead:
  1. Builds a running plain-text prompt in ReAct format (Thought / Action /
     Action Input / Observation / Final Answer).
  2. Calls the model for raw text output — no special fine-tuning needed.
  3. Parses Action + Action Input with regex, executes the tool, appends
     "Observation: <result>" and loops.
  4. Stops when the model writes "Final Answer: ..." or the round limit is hit.
"""

import asyncio
import json
import re
import logging
from typing import Callable, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from ..ragQuery_state import RAGQueryState
from ..rag_history import format_conversation_history
from ..response_formatting import humanize_final_answer


logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6

# ── Regex patterns ────────────────────────────────────────────────────────────

# Matches:  Action: get_requisition_candidates
_ACTION_RE = re.compile(r"Action\s*:\s*(\w+)", re.IGNORECASE)

# Matches the JSON object on the Action Input line (handles nested braces)
_INPUT_RE = re.compile(r"Action\s*Input\s*:\s*(\{.*?\})", re.IGNORECASE | re.DOTALL)

# Matches:  Final Answer: <everything after>
_FINAL_RE = re.compile(r"Final\s*Answer\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_action(text: str):
    """Return (tool_name, args_dict) or (None, None) if no action found."""
    action_match = _ACTION_RE.search(text)
    if not action_match:
        return None, None

    tool_name = action_match.group(1).strip()

    input_match = _INPUT_RE.search(text)
    raw_input = input_match.group(1).strip() if input_match else "{}"
    try:
        args = json.loads(raw_input)
    except json.JSONDecodeError:
        args = {}

    return tool_name, args


def _extract_final_answer(text: str) -> Optional[str]:
    m = _FINAL_RE.search(text)
    return m.group(1).strip() if m else None


_DETAIL_KEYWORDS = (
    "tell me more", "more about", "application detail", "about him", "about her",
    "about them", "his detail", "her detail", "their detail", "that candidate",
    "screening", "justification", "skills", "education", "experience", "background",
    "cv", "resume", "qualification", "why was", "why is",
)


def _needs_candidate_details(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _DETAIL_KEYWORDS)


# ── Node factory ──────────────────────────────────────────────────────────────

def make_llm_node(
    build_tools_fn: Callable[[int, int], List],
    build_prompt_fn: Callable[[Optional[int], int], str],
) -> Callable[[RAGQueryState], RAGQueryState]:
    """
    Factory that returns an async LLM node using the ReAct pattern.

    The returned node:
      - Extracts the latest HumanMessage from state["messages"]
      - Runs the ReAct loop (up to MAX_TOOL_ROUNDS tool calls)
      - Returns updated state with the final AIMessage appended
    """
    from stores.llm.llm_config import llm_rag  # import late to avoid circular deps

    async def llm_node(state: RAGQueryState) -> RAGQueryState:
        tools = build_tools_fn(state["user_id"], state["requisition_id"])
        system_prompt = build_prompt_fn(state["user_id"], state["requisition_id"])

        tool_registry = {
            getattr(t, "name", None) or getattr(t, "__name__", None): t
            for t in tools
            if getattr(t, "name", None) or getattr(t, "__name__", None)
        }

        tool_names = sorted(tool_registry.keys())

        logger.info(
            f"[llm_node] starting RAG loop requisition_id={state['requisition_id']} "
            f"user_id={state['user_id']} chat_thread_id={state.get('chat_thread_id')} "
            f"history_turns={max(0, len(state['messages']) - 1)} "
            f"available_tools={tool_names}"
        )
        logger.debug(f"[llm_node] initial query={state.get('query')!r}")

        # Extract the user's question from the last HumanMessage
        question = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            state.get("query", ""),
        )

        history_block = format_conversation_history(
            state["messages"],
            summary=state.get("conversation_summary"),
        )

        # Seed the ReAct prompt — model picks up from "Thought:"
        running = f"{system_prompt}\n\n{history_block}Question: {question}\nThought:"

        final_answer: Optional[str] = None
        tools_used = False
        tools_called: set[str] = set()

        for round_num in range(MAX_TOOL_ROUNDS):
            raw = await asyncio.to_thread(llm_rag.generate, running)
            text = raw["results"][0]["generated_text"].strip()

            logger.info(f"[llm_node] round {round_num + 1} model output received")
            logger.debug(f"[llm_node] model output:\n{text[:800]}")

            tool_name, args = _parse_action(text)
            final_answer = _extract_final_answer(text)

            # Execute tool calls before accepting a Final Answer in the same turn
            if tool_name is not None:
                logger.info(f"[llm_node] parsed tool_name={tool_name!r} args={args}")
                tool = tool_registry.get(tool_name)
                if tool is None:
                    observation = (
                        f"Error: unknown tool '{tool_name}'. "
                        f"Available tools: {tool_names}"
                    )
                    logger.warning(f"[llm_node] Unknown tool requested: '{tool_name}'")
                else:
                    try:
                        observation = await tool.ainvoke(args)
                        tools_used = True
                        tools_called.add(tool_name)
                        logger.info(f"[llm_node] tool '{tool_name}' invoked successfully")
                        logger.debug(f"[llm_node] tool observation: {str(observation)[:800]}")
                    except Exception as exc:
                        observation = f"Tool error: {exc}"
                        logger.exception(f"[llm_node] tool '{tool_name}' raised an exception")

                running = running + "\n" + text + f"\nObservation: {observation}\nThought:"
                continue

            if final_answer and tools_used:
                if _needs_candidate_details(question) and "get_candidate_details" not in tools_called:
                    logger.info(
                        "[llm_node] detail question answered from summary only — "
                        "nudging model to call get_candidate_details"
                    )
                    running = (
                        running + "\n" + text
                        + "\nObservation: The candidate list summary is not enough for this question. "
                          "Call get_candidate_details with the relevant candidate_id "
                          "(from the list above or prior conversation) before writing Final Answer.\nThought:"
                    )
                    continue
                logger.info("[llm_node] final answer detected after tool use, breaking loop")
                break

            # No Action in this turn — nudge toward tool use or a proper Final Answer
            logger.info(f"[llm_node] parsed tool_name={tool_name!r} args={args}")
            nudge = (
                "Please use a tool before answering."
                if final_answer and not tools_used
                else "The model did not choose a tool. "
                     "Please select one of the available tools and provide valid Action Input."
            )
            logger.warning("[RAG] Model output contained no tool action — retrying")
            running = running + "\n" + text + f"\nObservation: {nudge}\nThought:"
            continue

        # If we exhausted rounds without a Final Answer, force one last generation
        if not final_answer:
            nudge = (
                running
                + "\nI now have enough information to answer using only the observed tool outputs.\n"
                "Write Final Answer in recruiter-friendly Markdown (tables and bullet lists). "
                "Do NOT paste raw JSON.\nFinal Answer:"
            )
            raw = await asyncio.to_thread(llm_rag.generate, nudge)
            final_answer = raw["results"][0]["generated_text"].strip()
            final_answer = _extract_final_answer("Final Answer: " + final_answer) or final_answer

        if final_answer:
            final_answer = humanize_final_answer(final_answer)

        response_msg = AIMessage(content=final_answer)
        return {
            **state,
            "messages": state["messages"] + [response_msg],
            "response": final_answer,
        }

    return llm_node
