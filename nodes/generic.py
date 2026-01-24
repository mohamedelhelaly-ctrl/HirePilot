from models.state import ApplicationState
from models.conversation import ConversationStore
from config.llm_config import llm_generic
from prompts.generic_prompt import get_generic_prompt
from utils.html_formatter import format_response_as_html

def generic_node(state: ApplicationState) -> ApplicationState:
    """Generic question handler node"""
    
    print("💬 Generic question node...")
    
    user_input = state.get("user_input", "")
    thread_id = state.get("thread_id", "")
    
    # Get conversation context
    conv_store = ConversationStore(thread_id)
    conversation_context = conv_store.get_context()
    
    # Generate prompt
    prompt = get_generic_prompt(
        user_input,
        state.get("jd_available", False),
        state.get("cvs_available", False),
        state.get("screening_complete", False),
        state.get("num_cvs", 0),
        len(state.get("screening_results", [])) if state.get("screening_results") else 0,
        conversation_context
    )
    
    # Get response
    response = llm_generic.generate(prompt)
    response_text = response['results'][0]['generated_text'].strip()
    state["response_json"] = {"response": response_text}
    state["response_message"] = response_text  # Set for frontend
    print("✅ Generic response generated")
    return state