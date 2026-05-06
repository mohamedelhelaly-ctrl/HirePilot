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

from ..state import RAGQueryState

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
    from utils.llm_config import llm_rag  # import late to avoid circular deps

    async def llm_node(state: RAGQueryState) -> RAGQueryState:
        tools = build_tools_fn(state["user_id"], state["requisition_id"])
        system_prompt = build_prompt_fn(state["user_id"], state["requisition_id"])

        tool_registry = {t.name: t for t in tools}

        # Extract the user's question from the last HumanMessage
        question = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            state.get("query", ""),
        )

        # Seed the ReAct prompt — model picks up from "Thought:"
        running = f"{system_prompt}\n\nQuestion: {question}\nThought:"

        final_answer: Optional[str] = None

        for round_num in range(MAX_TOOL_ROUNDS):
            raw = await asyncio.to_thread(llm_rag.generate, running)
            text = raw["results"][0]["generated_text"].strip()

            logger.debug(f"[RAG round {round_num + 1}] model output:\n{text[:300]}")

            # Check for a final answer anywhere in what we have so far
            final_answer = _extract_final_answer(text)
            if final_answer:
                break

            # Try to parse a tool call
            tool_name, args = _parse_action(text)
            if tool_name is None:
                # Model gave free text without an Action — treat as final answer
                final_answer = text
                break

            # Execute the tool
            tool = tool_registry.get(tool_name)
            if tool is None:
                observation = (
                    f"Error: unknown tool '{tool_name}'. "
                    f"Available tools: {list(tool_registry.keys())}"
                )
                logger.warning(f"[RAG] Unknown tool requested: '{tool_name}'")
            else:
                try:
                    observation = await tool.ainvoke(args)
                    logger.debug(f"[RAG] Tool '{tool_name}' returned: {str(observation)[:200]}")
                except Exception as exc:
                    observation = f"Tool error: {exc}"
                    logger.warning(f"[RAG] Tool '{tool_name}' raised: {exc}")

            # Append result and prompt for next Thought
            running = running + "\n" + text + f"\nObservation: {observation}\nThought:"

        # If we exhausted rounds without a Final Answer, force one last generation
        if not final_answer:
            nudge = running + " I now have enough information to answer.\nFinal Answer:"
            raw = await asyncio.to_thread(llm_rag.generate, nudge)
            final_answer = raw["results"][0]["generated_text"].strip()
            # Strip any residual ReAct artefacts the model may prepend
            final_answer = _extract_final_answer("Final Answer: " + final_answer) or final_answer

        response_msg = AIMessage(content=final_answer)
        return {
            **state,
            "messages": state["messages"] + [response_msg],
            "response": final_answer,
        }

    return llm_node
