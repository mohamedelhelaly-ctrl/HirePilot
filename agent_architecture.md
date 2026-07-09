# LangGraph Agent Architecture Guide

A detailed breakdown of how this agent is structured — written so the same pattern can be lifted and applied to any domain with different data models and CRUD operations.

---

## Overview

The system is a **single-agent LangGraph application** with a Streamlit frontend. The agent is scoped to one entity at a time and allows the user to ask natural-language questions that get answered by calling real database-backed tools.

The agent is a compiled `StateGraph` that runs one node: an async LLM node that calls tools, reasons over the results, and streams a final answer back to the UI.

---

## The LLM: Groq via LangChain

The LLM is configured once in `config.py` and imported everywhere else.

```python
# config.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_tokens=2048,
    streaming=True,
)
```

```bash
pip install langchain-groq
```

```env
# .env
GROQ_API_KEY=your_key_here
```

**Why this matters:** `llm` is a plain LangChain `BaseChatModel`. Because of this, it works with `.bind_tools()`, `.ainvoke()`, and `.astream()` — the same interface regardless of which provider you swap in. Switching providers only requires changing `config.py`. Everything else in the codebase is provider-agnostic.

---

## Project Structure

```
your_agent/
├── config.py              # LLM instantiation — one place, imported everywhere
├── agent.py               # Compiles and exports the StateGraph
├── utils/
│   ├── state.py           # AgentState TypedDict — the shared data contract
│   ├── nodes.py           # make_llm_node() factory — the core agentic loop
│   └── tools.py           # All @tool definitions
└── prompts/
    └── prompt.py          # System prompt builder
```

---

## 1. State — `state.py`

```python
class AgentState(TypedDict):
    session_id: str
    messages: list[BaseMessage]
    user_email: str
    requisition_id: Optional[str]
    candidate_id: Optional[str]
```

`AgentState` is the **single data contract** that flows through every node of the graph. Think of it as the "request context" that every function in the system can read from.

**Key design decisions:**
- `messages` holds the full conversation history as LangChain `BaseMessage` objects (`HumanMessage`, `AIMessage`, `ToolMessage`). The agentic loop appends to this list each round — this is how the agent remembers what tools it already called and what they returned.
- `requisition_id` scopes every tool call. It is set once by the UI before the graph runs and never changes mid-conversation.
- `candidate_id` is optional — it pre-focuses the agent on a specific candidate if the user has one selected in the sidebar.
- `user_email` is threaded into every service call for authorization.

**When adapting this:** Replace `requisition_id` / `candidate_id` with whatever scoping identifiers your domain needs — e.g. `project_id`, `customer_id`, `order_id`. The pattern stays identical.

---

## 2. Tools — `tools.py`

Tools are the agent's **only way to read data**. They are async Python functions decorated with `@tool` and defined inside a factory function so they can close over the scoping context (`user_email`, `requisition_id`) without needing those values as arguments at call time.

```python
def build_candidates_tools(user_email: str, requisition_id: str):

    @tool
    async def get_candidates_summary() -> str:
        """
        Get a summary list of all candidates for this requisition: name, email,
        years of experience, screen score, tech score, CBI score, and status.
        Sorted by screen score descending. Use this for ranking or comparing
        candidates at a high level.
        """
        async with AsyncSessionLocal() as db:
            service = CandidatesSummaryService(thread_id=requisition_id, db=db)
            result = await service.summary()
        return result.model_dump_json()

    @tool
    async def get_candidate_details(candidate_id: str) -> str:
        """
        Get full profile details for a single candidate: all extracted CV fields,
        scores, assessment results, and a CV download URL.
        Use this when the user asks about a specific candidate by name or ID.
        """
        async with AsyncSessionLocal() as db:
            service = CandidateDetailsService(
                candidate_id=candidate_id,
                thread_id=requisition_id,
                email=user_email,
                db=db,
            )
            result = await service.get_details()
        return json.dumps(result.model_dump())

    return [
        get_candidates_summary,
        get_candidate_details,
        # ... other tools
    ]
```

**Critical patterns to understand:**

**1. Closure over context** — `user_email` and `requisition_id` are captured from the outer factory function. The tools themselves take zero or minimal arguments, which means the LLM never has to know or pass the scoping IDs — they are always pre-baked in at construction time.

**2. Docstrings are instructions to the LLM** — the `@tool` decorator exposes the function's docstring as the tool's description in the model's tool-use schema. Write them clearly: what data the tool returns, and *when* the LLM should call it. The LLM reads these to decide which tool to use and in what order.

**3. Always return a string** — tools return `model_dump_json()` or `json.dumps(...)`. The LLM receives raw string content in a `ToolMessage`, so serializing to JSON is the most reliable format.

**4. Each tool maps to one service method** — tools are thin wrappers. All real database logic lives in the service layer. The tool just opens a DB session, calls the service, and serializes the result. Keep tools dumb; keep services smart.

**When adapting this:** Keep the factory pattern (`build_your_tools(user_id, scope_id)`). Replace the service calls inside each tool with your own CRUD/read operations. Rewrite the docstrings to match your domain — the docstrings are what the LLM uses to reason about which tool to call and when.

---

## 3. The Agentic Loop — `nodes.py`

This is the heart of the system. The `make_llm_node()` factory returns an async function that LangGraph registers as a graph node. When the graph runs, this node:

1. Builds the tools and system prompt from the current state.
2. Binds the tools to the LLM.
3. Runs a **tool-calling loop** — up to 5 rounds where the LLM can request tools, get results, and reason further before answering.
4. Streams the final text response token by token back to the UI.

```python
def make_llm_node(build_tools_fn, build_prompt_fn):

    async def llm_node(state: AgentState) -> AgentState:
        writer = get_stream_writer()  # LangGraph's custom stream writer

        # 1. Build tools and prompt from state
        tools = build_tools_fn(state["user_email"], state["requisition_id"])
        system_prompt = build_prompt_fn(
            state["user_email"],
            state["requisition_id"],
            state.get("candidate_id")
        )

        tool_registry = {t.name: t for t in tools}
        llm_with_tools = llm.bind_tools(tools)

        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        # 2. Agentic loop — keep calling tools until the LLM produces text
        MAX_TOOL_ROUNDS = 5
        for _ in range(MAX_TOOL_ROUNDS):
            response = await llm_with_tools.ainvoke(messages)

            if not response.tool_calls:
                break  # LLM decided it has enough info — exit loop

            # Execute every tool the LLM requested this round
            tool_results = []
            for tool_call in response.tool_calls:
                tool_fn = tool_registry.get(tool_call["name"])
                result = await tool_fn.ainvoke(tool_call["args"]) if tool_fn else "Tool not found."
                tool_results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

            # Append assistant turn + tool results so the next iteration sees them
            messages = messages + [response] + tool_results

        # 3. Stream the final answer token by token
        full_response = ""
        async for chunk in llm_with_tools.astream(messages):
            if chunk.content:
                full_response += chunk.content
                writer({"token": chunk.content})  # sends token to the UI in real time

        # 4. Return updated state with the new AI message appended
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=full_response)],
        }

    return llm_node
```

**How the tool-calling loop works step by step:**

```
User asks: "Who is the top candidate?"
         │
         ▼
LLM receives: system prompt + full conversation history
         │
         ▼
LLM responds with tool_calls: [get_candidates_summary()]
         │
         ▼
Node executes get_candidates_summary() → returns JSON list of candidates
         │
         ▼
ToolMessage added to messages list
         │
         ▼
LLM invoked again — now sees the tool result in its context
         │
         ▼
LLM responds with NO tool_calls → loop exits
         │
         ▼
Final answer streamed token by token to the UI
```

The LLM may call **multiple tools in a single round** (e.g. summary and details at the same time), or chain tools across multiple rounds (e.g. first list candidates to find an ID, then fetch details for that ID). The loop handles both cases naturally.

**`get_stream_writer()`** is a LangGraph utility that returns a callable. Calling `writer({"token": "..."})` pushes data into LangGraph's custom stream, which the frontend consumes in real time. This is what makes the response appear to type out character by character in the UI.

**`make_llm_node` is fully domain-agnostic** — it receives `build_tools_fn` and `build_prompt_fn` as arguments. You never edit this file when changing domains. You only swap in different tool builders and prompt builders.

---

## 4. System Prompt — `prompt.py`

The system prompt is built dynamically as a plain string, injecting the session context at runtime:

```python
def build_candidates_prompt(
    user_email: str,
    requisition_id: str,
    candidate_id: Optional[str] = None,
) -> str:
    context_parts = [
        f"- Requisition ID (always use this — never ask the user for it): {requisition_id}",
    ]
    if candidate_id:
        context_parts.append(
            f"- The user is currently focused on candidate ID: {candidate_id}"
        )

    return f"""You are a Talent Acquisition Assistant helping recruiters evaluate candidates.

## Current session context
- User: {user_email}
{chr(10).join(context_parts)}

## Tools available
- get_candidates_summary: ranked list of all candidates with scores and status.
- get_candidate_details: full profile for a single candidate (pass candidate_id).
- get_screening_table: detailed breakdown of all candidates with all fields.
- get_requisition_details: the job description and required skills for this role.

## Response style
- Always respond in Markdown format.
- Write in natural flowing paragraphs, not bullet points.
- Use tables only when directly comparing multiple candidates side by side.

## Behavior rules
- The requisition_id is already baked into your tools — never ask the user for it.
- If the user mentions a candidate by name, call get_candidates_summary first to find the ID,
  then call get_candidate_details with that ID.
- If a candidate_id is in the context above, use it as the default without asking.
- If a tool returns empty, say so clearly rather than guessing.
- You are READ-ONLY. You cannot create, update, or delete anything. If the user asks you
  to make a change, tell them to use the platform UI.
"""
```

**Key things the system prompt must do:**

- **Tell the LLM its current scope** — inject `requisition_id`, `user_email`, `candidate_id` so the LLM understands what it is operating on.
- **Describe each tool and when to use it** — even though this is also in the tool docstrings, reinforcing it in the prompt improves reliability and multi-step reasoning.
- **Set hard behavioral rules** — read-only enforcement, how to resolve names to IDs, what to say when a tool returns nothing.
- **Define response style** — Markdown, prose over bullets, when to use tables, tone.

**When adapting this:** Keep the same four sections (context, tools, style, rules). Just inject whatever context your domain needs and describe your tools. The behavioral rules section is especially important — it prevents hallucination and misuse of tools.

---

## 5. Graph Assembly — `agent.py`

```python
from langgraph.graph import StateGraph, END
from .utils.state import AgentState
from .utils.nodes import make_llm_node
from .utils.tools import build_candidates_tools
from .prompts.prompt import build_candidates_prompt

_node = make_llm_node(build_candidates_tools, build_candidates_prompt)

builder = StateGraph(AgentState)
builder.add_node("llm", _node)
builder.set_entry_point("llm")
builder.add_edge("llm", END)

graph = builder.compile()
```

This is intentionally minimal. The graph has **one node** (`llm`) that runs, then immediately ends. All the complexity — tool calling, multi-round looping, streaming — is handled *inside* that node, not by the graph topology.

`graph` is the compiled object the Streamlit app imports and calls with `graph.astream(input_state, stream_mode="custom")`.

**When adapting this:** For most use cases, the single-node structure is all you need. You only need multiple graph nodes if you have genuinely separate processing stages (e.g. a classification step before the LLM, or a validation step after). Don't add graph complexity unless you have a real reason.

---

## 6. Frontend Streaming — `app.py`

The Streamlit app constructs the input state, kicks off the graph in a background async loop, and renders tokens as they arrive.

```python
# The input fed into the graph on every user message
input_state = {
    "session_id": st.session_state.session_id,
    "messages": st.session_state.messages,   # full history passed every time
    "user_email": st.session_state.user_email,
    "requisition_id": st.session_state.requisition_id or None,
    "candidate_id": st.session_state.candidate_id or None,
}

# Coroutine that reads from the graph stream and puts tokens into a queue
async def _stream(q: queue.Queue):
    async for chunk in active_graph.astream(input_state, stream_mode="custom"):
        if isinstance(chunk, dict) and "token" in chunk:
            q.put(chunk["token"])
    q.put(None)  # sentinel — signals that streaming is done

# Run the coroutine in a dedicated background event loop
future = asyncio.run_coroutine_threadsafe(_stream(token_queue), _get_agent_loop())

# Main thread reads from the queue and updates the UI
while True:
    token = token_queue.get()
    if token is None:
        break
    streamed_tokens += token
    placeholder.markdown(streamed_tokens, unsafe_allow_html=True)
```

**How streaming works end-to-end:**

```
nodes.py          writer({"token": "Hello"})
                      │
                      │  LangGraph pushes into custom stream
                      ▼
graph.astream()   yields {"token": "Hello"} as an async chunk
                      │
                      ▼
_stream()         token_queue.put("Hello")
                      │
                      ▼
Main thread       streamed_tokens += "Hello"
                  placeholder.markdown(streamed_tokens)  →  live UI update
```

The async graph runs in a **dedicated background event loop** (created once, cached by Streamlit via `@st.cache_resource`). This avoids conflicts between Streamlit's synchronous rendering model and the async LangGraph execution. The `queue.Queue` bridges the two threads safely — the async side puts tokens in, the sync side takes them out.

Note that **the full message history is passed in on every turn** — the graph has no built-in memory. Persistence is managed entirely in `st.session_state.messages`, which grows with each exchange and is always included in `input_state`.

**When adapting this:** The streaming plumbing (`token_queue`, `_get_agent_loop`, `run_coroutine_threadsafe`) is boilerplate you can copy verbatim. The only thing you change is the keys in `input_state` to match your `AgentState`.

---

## Adapting This to a New Domain — Checklist

| Step | File | What to change |
|---|---|---|
| **State** | `state.py` | Define your scoping IDs and any extra context fields |
| **Services** | `your_service.py` | Write async service/repository classes with your DB queries |
| **Tools** | `tools.py` | Wrap each service method in a `@tool` inside a factory; write clear docstrings |
| **Prompt** | `prompt.py` | Inject your context, describe your tools, write your behavioral rules |
| **Node** | `nodes.py` | Copy as-is — it is fully domain-agnostic |
| **Graph** | `agent.py` | Copy the single-node pattern; only swap the tool and prompt builders |
| **Config** | `config.py` | Point at your LLM provider |
| **Frontend** | `app.py` | Copy streaming plumbing verbatim; only update `input_state` keys |

The only files that contain domain-specific logic are **tools**, **prompt**, and **services**. Everything else — apart from the state shape — is reusable infrastructure you don't need to touch.
