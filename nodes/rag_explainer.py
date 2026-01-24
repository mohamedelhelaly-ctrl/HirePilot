import re
from models.state import ApplicationState
from utils.rag_retrieval import RAGRetrieval
from config.llm_config import llm_rag
from prompts.rag_prompt import get_rag_prompt
from database.schema import get_db_connection

def extract_candidate_ids(user_input: str, thread_id: str) -> list:
    """Extract candidate IDs from user input"""
    
    candidate_ids = set()
    
    patterns = [
        r'candidate[s]?\s*#?(\d+)',
        r'cand[s]?\s*#?(\d+)',
        r'(?:id|ids)\s*#?(\d+)',
        r'#(\d+)',
        r'\bvs\b\s*#?(\d+)',
        r'\band\b\s*#?(\d+)',
        r'(?<!\d)(\d+)\b(?![\d\w])',
    ]
    
    user_input_lower = user_input.lower()
    for pattern in patterns:
        matches = re.finditer(pattern, user_input_lower)
        for match in matches:
            id_str = match.group(1)
            if id_str.isdigit():
                candidate_ids.add(int(id_str))
    
    # Validate against database
    if candidate_ids:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(candidate_ids))
        cursor.execute(
            f"SELECT candidate_id FROM candidates WHERE candidate_id IN ({placeholders}) AND thread_id = ?",
            (*list(candidate_ids), thread_id)
        )
        valid_ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        return sorted(list(valid_ids))
    
    # Fallback to top 5
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT candidate_id FROM candidates WHERE thread_id = ? ORDER BY CAST(score AS REAL) DESC LIMIT 5",
        (thread_id,)
    )
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results

def rag_explainer_node(state: ApplicationState) -> ApplicationState:
    """RAG-based candidate explanation node"""
    
    print("🧠 RAG explainer node...")
    
    user_input = state.get("user_input", "")
    thread_id = state.get("thread_id")
    job_description = state.get("job_description", "")
    
    # Extract candidate IDs
    candidate_ids = extract_candidate_ids(user_input, thread_id)
    
    if not candidate_ids:
        state["response_json"] = {"error": "No candidates found. Please specify candidate IDs or complete screening first."}
        state["response_message"] = "No candidates found. Please specify candidate IDs or complete screening first."
        return state
    
    print(f"📋 Analyzing candidates: {candidate_ids}")
    
    try:
        # Initialize RAG
        rag = RAGRetrieval(thread_id)
        rag.ensure_indexed(candidate_ids)
        retrieved_docs = rag.retrieve_candidates(user_input, candidate_ids, top_k=10)
        if not retrieved_docs:
            state["response_json"] = {"error": "Could not retrieve candidate information."}
            state["response_message"] = "Could not retrieve candidate information."
            return state
        # Build context
        context_parts = []
        for doc in retrieved_docs:
            context_parts.append(f"=== Candidate {doc['metadata']['candidate_id']} ===")
            context_parts.append(doc['content'])
            context_parts.append("")
        context = "\n".join(context_parts)
        # Generate explanation
        prompt = get_rag_prompt(user_input, context, job_description)
        response = llm_rag.generate(prompt)
        explanation = response['results'][0]['generated_text'].strip()
        # Extract conclusion
        import re
        conclusion_match = re.search(r'###\s*Conclusion\s*(.*)', explanation, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            summary_text = conclusion_match.group(1).strip()
            explanation_no_conclusion = re.sub(r'###\s*Conclusion\s*.*', '', explanation, flags=re.DOTALL | re.IGNORECASE).strip()
        else:
            summary_text = "Analysis complete."
            explanation_no_conclusion = explanation
        # Get candidate info
        from database.schema import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(candidate_ids))
        cursor.execute(
            f"SELECT candidate_id, english_name, score FROM candidates WHERE candidate_id IN ({placeholders}) AND thread_id = ?",
            (*candidate_ids, thread_id)
        )
        candidate_info = {row[0]: {"name": row[1], "score": row[2]} for row in cursor.fetchall()}
        conn.close()
        candidates = []
        for cid in candidate_ids:
            if cid in candidate_info:
                candidates.append({
                    "candidate_id": cid,
                    "name": candidate_info[cid]["name"] or f"Candidate {cid}",
                    "score": candidate_info[cid]["score"]
                })
        # Build JSON response
        state["response_json"] = {
            "candidates": candidates,
            "summary": summary_text,
            "detailed_analysis": explanation_no_conclusion
        }
        # Format message for frontend
        candidate_names = ", ".join([c["name"] for c in candidates])
        state["response_message"] = f"Analysis for {candidate_names}:\n\n{summary_text}\n\n{explanation_no_conclusion}"
        print("✅ RAG explanation generated")
    except Exception as e:
        state["response_json"] = {"error": f"Error generating explanation: {str(e)}"}
        state["response_message"] = f"Error generating explanation: {str(e)}"
        print(f"❌ RAG error: {e}")
        import traceback
        traceback.print_exc()
    return state