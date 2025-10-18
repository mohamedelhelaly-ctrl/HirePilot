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
        state["response_message"] = "<p>❌ No candidates found. Please specify candidate IDs or complete screening first.</p>"
        return state
    
    print(f"📋 Analyzing candidates: {candidate_ids}")
    
    try:
        # Initialize RAG
        rag = RAGRetrieval(thread_id)
        
        # Ensure candidates are indexed
        rag.ensure_indexed(candidate_ids)
        
        # Retrieve relevant documents
        retrieved_docs = rag.retrieve_candidates(user_input, candidate_ids, top_k=10)
        
        if not retrieved_docs:
            state["response_message"] = "<p>❌ Could not retrieve candidate information.</p>"
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
        conclusion_match = re.search(r'###\s*Conclusion\s*(.*)', explanation, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            summary_text = conclusion_match.group(1).strip().replace('\n', '<br>')
            explanation_no_conclusion = re.sub(r'###\s*Conclusion\s*.*', '', explanation, flags=re.DOTALL | re.IGNORECASE).strip()
        else:
            summary_text = "Analysis complete."
            explanation_no_conclusion = explanation
        
        # Convert markdown to HTML
        detailed_html = explanation_no_conclusion.replace('\n\n', '</p><p>')
        detailed_html = detailed_html.replace('\n', '<br>')
        detailed_html = re.sub(r'###\s*(.*?)(?=(?:<br>|</p>|\Z))', r'<h3>\1</h3>', detailed_html)
        detailed_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', detailed_html)
        
        # Get candidate info for chips
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(candidate_ids))
        cursor.execute(
            f"SELECT candidate_id, english_name, score FROM candidates WHERE candidate_id IN ({placeholders}) AND thread_id = ?",
            (*candidate_ids, thread_id)
        )
        candidate_info = {row[0]: {"name": row[1], "score": row[2]} for row in cursor.fetchall()}
        conn.close()
        
        # Create candidate chips
        candidate_chips = ""
        for cid in candidate_ids:
            if cid in candidate_info:
                name = candidate_info[cid]["name"] or f"Candidate {cid}"
                score = candidate_info[cid]["score"]
                try:
                    score_float = float(score)
                    score_color = "#10b981" if score_float >= 80 else "#f59e0b" if score_float >= 60 else "#ef4444"
                except:
                    score_color = "#6b7280"
                
                candidate_chips += f"""
                <div style="display: inline-block; margin: 5px 8px 5px 0; padding: 8px 16px; 
                            background: linear-gradient(135deg, {score_color}15 0%, {score_color}25 100%);
                            border: 1.5px solid {score_color}40; border-radius: 20px; font-size: 13px;">
                    <span style="font-weight: 600; color: {score_color};">#{cid}</span>
                    <span style="margin-left: 6px;">{name}</span>
                    <span style="color: {score_color}; margin-left: 8px; font-weight: 600;">
                        {score}%
                    </span>
                </div>
                """
        
        # Build HTML response
        html_response = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <header style="margin-bottom: 16px;">
                <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 4px;">🎯 Candidate Analysis</h2>
                <p style="margin: 0; color: #6b7280;">AI-powered insights based on CV content and job requirements</p>
            </header>
            
            <section style="margin-bottom: 16px;">
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Candidates Analyzed</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    {candidate_chips}
                </div>
            </section>
            
            <section style="margin-bottom: 16px;">
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Summary</h3>
                <p style="margin: 0;">{summary_text}</p>
            </section>
            
            <details style="margin-top: 16px;">
                <summary style="font-size: 15px; font-weight: 600; cursor: pointer; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    View Detailed Analysis
                </summary>
                <div style="margin-top: 12px; padding: 15px; border-left: 3px solid #0066cc; background: #f8f9fa;">
                    {detailed_html}
                </div>
            </details>
        </div>
        """
        
        state["response_message"] = html_response
        print("✅ RAG explanation generated")
        
    except Exception as e:
        state["response_message"] = f"<p>❌ Error generating explanation: {str(e)}</p>"
        print(f"❌ RAG error: {e}")
        import traceback
        traceback.print_exc()
    
    return state