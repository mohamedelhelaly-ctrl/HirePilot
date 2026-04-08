"""
LLM node factory for the RAG query agent.

Provides the agentic loop with tool-calling.
"""

from typing import Callable, List, Optional
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..config import llm
from ..state import RAGQueryState


def make_llm_node(
    build_tools_fn: Callable[[int, int], List[BaseTool]],
    build_prompt_fn: Callable[[Optional[int], int], str]
) -> Callable[[RAGQueryState], RAGQueryState]:
    """
    Factory that returns an async LLM node function.
    
    The node runs a tool-calling loop: LLM calls tools, gets results, reasons further, then answers.
    """

    async def llm_node(state: RAGQueryState) -> RAGQueryState:
        # Build tools and prompt from state
        tools = build_tools_fn(state["user_id"], state["requisition_id"])
        system_prompt = build_prompt_fn(state["user_id"], state["requisition_id"])

        tool_registry = {t.name: t for t in tools}
        llm_with_tools = llm.bind_tools(tools)

        # Start with system prompt + conversation history
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        # Agentic loop — up to 5 rounds of tool calling
        MAX_TOOL_ROUNDS = 5
        for _ in range(MAX_TOOL_ROUNDS):
            response = await llm_with_tools.ainvoke(messages)

            if not response.tool_calls:
                break  # LLM decided it has enough info

            # Execute all requested tools
            tool_results = []
            for tool_call in response.tool_calls:
                try:
                    tool = tool_registry[tool_call["name"]]
                    args = tool_call["args"]
                    result = await tool.ainvoke(args)
                    tool_results.append(ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"]
                    ))
                except Exception as e:
                    tool_results.append(ToolMessage(
                        content=f"Tool execution failed: {str(e)}",
                        tool_call_id=tool_call["id"]
                    ))

            messages = messages + [response] + tool_results

        # Final response
        final_response = await llm_with_tools.ainvoke(messages)
        
        # Return updated state with the final answer
        return {
            **state,
            "messages": state["messages"] + [final_response],
            "response": final_response.content,
        }

    return llm_node
