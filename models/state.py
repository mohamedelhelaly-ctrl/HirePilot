from typing import Dict, List, Any, Optional, TypedDict

class ApplicationState(TypedDict):
    """Application state for LangGraph workflow"""
    
    # Core input
    user_input: str
    thread_id: str
    
    # Conversation tracking
    conversation_summary: str
    recent_messages: List[Dict[str, str]]
    
    # Status flags
    jd_available: bool
    cvs_available: bool
    screening_complete: bool
    
    # Data storage
    job_description: Optional[str]
    num_cvs: int
    retrieved_n_cvs: int
    
    # Results
    screening_results: Optional[List[Dict]]
    
    # Routing
    current_intent: Optional[str]
    response_message: str
    error_message: Optional[str]