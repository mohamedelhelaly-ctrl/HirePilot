from models.state import ApplicationState
from models.conversation import ConversationStore
from config.llm_config import llm_routing
from prompts.routing_prompt import get_routing_prompt

def routing_node(state: ApplicationState) -> ApplicationState:
    """Intent classification node"""
    
    print("🔀 Routing node - classifying intent...")
    
    user_input = state.get("user_input", "")
    thread_id = state.get("thread_id", "")
    
    # Get conversation context
    conv_store = ConversationStore(thread_id)
    conversation_context = conv_store.get_context()
    
    # Generate classification prompt
    prompt = get_routing_prompt(
        user_input,
        state.get("jd_available", False),
        state.get("cvs_available", False),
        state.get("screening_complete", False),
        conversation_context
    )
    
    # Get intent from LLM
    response = llm_routing.generate(prompt)
    intent = response['results'][0]['generated_text'].strip().lower()
    
    # Clean intent
    intent = intent.replace(".", "").replace(":", "").strip()
    
    valid_intents = ["screen_cvs", "explain_candidate", "talk_to_data", "generic_question"]
    if intent not in valid_intents:
        intent = "generic_question"
    
    state["current_intent"] = intent
    print(f"✅ Intent classified: {intent}")
    
    return state