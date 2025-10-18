def get_routing_prompt(user_message: str, jd_available: bool, cvs_available: bool, 
                       screening_complete: bool, conversation_context: str) -> str:
    """Intent classification prompt"""
    
    prompt = f"""You are an intent classification engine for a recruitment system.

Classify the user's message into exactly ONE category:
- screen_cvs: User wants to screen/rank CVs against the job description
- explain_candidate: User asks WHY/HOW candidate scored, comparisons, qualitative analysis
- talk_to_data: User wants to query/filter data (count, list, show candidates with X)
- generic_question: General questions, greetings, or anything else

System Context:
- Job Description Available: {"Yes" if jd_available else "No"}
- CVs Available: {"Yes" if cvs_available else "No"}
- Screening Complete: {"Yes" if screening_complete else "No"}

Conversation Context:
{conversation_context}

Decision Rules:

1. **screen_cvs**: User wants comprehensive CV screening
   - "screen the CVs", "rank candidates", "match to job description"
   - Only if JD and CVs are available

2. **explain_candidate**: Qualitative analysis (WHY/HOW)
   - "why did candidate X score...", "explain candidate Y's fit"
   - "compare candidate A and B", "what makes X suitable"
   - Only if screening is complete

3. **talk_to_data**: Quantitative queries (COUNT/LIST/FILTER)
   - "how many candidates...", "show candidates with...", "list all..."
   - Only if screening is complete

4. **generic_question**: Everything else
   - Greetings, system questions, unclear requests

User Message: "{user_message}"

Respond with ONLY the category name (no explanation):"""
    
    return prompt