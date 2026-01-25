from langgraph.graph import StateGraph, END
from models.state import ApplicationState
from nodes.routing import routing_node
from nodes.generic import generic_node
from nodes.screening import screening_node
from nodes.rag_explainer import rag_explainer_node
from nodes.talk_to_data import talk_to_data_node
from models.conversation import ConversationStore

def route_by_intent(state: ApplicationState) -> str:
    """Route based on classified intent"""
    return state.get("current_intent", "generic_question")

def create_workflow():
    """Create LangGraph workflow"""
    
    workflow = StateGraph(ApplicationState)
    
    # Add nodes
    workflow.add_node("routing", routing_node)
    workflow.add_node("generic_question", generic_node)
    workflow.add_node("screen_cvs", screening_node)
    workflow.add_node("explain_candidate", rag_explainer_node)
    workflow.add_node("talk_to_data", talk_to_data_node)
    
    # Set entry point
    workflow.set_entry_point("routing")
    
    # Add conditional routing
    workflow.add_conditional_edges(
        "routing",
        route_by_intent,
        {
            "generic_question": "generic_question",
            "screen_cvs": "screen_cvs",
            "explain_candidate": "explain_candidate",
            "talk_to_data": "talk_to_data"
        }
    )
    
    # All nodes end the workflow
    workflow.add_edge("generic_question", END)
    workflow.add_edge("screen_cvs", END)
    workflow.add_edge("explain_candidate", END)
    workflow.add_edge("talk_to_data", END)
    
    app = workflow.compile()
    print("✅ Workflow compiled successfully")
    return app

def run_workflow(user_input: str, thread_id: str, job_object: dict = None) -> dict:
    """Run the workflow"""
    
    print(f"\n{'='*60}")
    print(f"🎯 Processing: {user_input}")
    print(f"🔗 Thread: {thread_id}")
    print(f"{'='*60}\n")
    
    # Check if CVs exist for thread
    import os
    cvs_dir = f"assets/cvs/{thread_id}"
    cvs_available = os.path.exists(cvs_dir) and len([f for f in os.listdir(cvs_dir) if f.endswith('.pdf')]) > 0
    
    # Check screening status
    from database.schema import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM candidates WHERE thread_id = ?", (thread_id,))
    screening_complete = cursor.fetchone()[0] > 0
    conn.close()
    
    # Initialize state
    initial_state = ApplicationState(
        user_input=user_input,
        thread_id=thread_id,
        conversation_summary="",
        recent_messages=[],
        jd_available=job_object is not None,
        cvs_available=cvs_available,
        screening_complete=screening_complete,
        job_object=job_object,
        job_description=job_object.get("details", job_object.get("description", "")) if job_object else None,
        num_cvs=0,
        retrieved_n_cvs=20,
        screening_results=None,
        current_intent=None,
        response_message="",
        error_message=None
    )
    
    # Run workflow
    workflow_app = create_workflow()
    result_state = workflow_app.invoke(initial_state)
    
    # Save conversation
    conv_store = ConversationStore(thread_id)
    conv_store.add_message("user", user_input)
    conv_store.add_message("assistant", result_state.get("response_message", ""))
    
    print(f"\n{'='*60}")
    print("✅ Workflow completed")
    print(f"{'='*60}\n")
    
    return result_state