"""
State schema for the RAG query subgraph using agent architecture.
The subgraph runs a single LLM node with tool-calling loop.
"""

from typing import Optional, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class RAGQueryState(TypedDict):
    # Input fields
    query: str
    """User's natural language question about candidates"""
    
    requisition_id: int
    """Requisition context for scoped search"""
    
    user_id: Optional[int]
    """User making the query (for access control and logging)"""
    
    # Agent fields
    messages: List[BaseMessage]
    """Conversation history for the agentic loop"""
    
    # Output
    response: str
    """Final response from the agent"""
