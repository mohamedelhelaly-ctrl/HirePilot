import threading
from models.state import ApplicationState
from utils.screening_engine import screen_cvs
from utils.html_formatter import dataframe_to_html
from utils.rag_retrieval import index_all_candidates_for_thread

def background_rag_indexing(thread_id: str):
    """Background task to index candidates for RAG"""
    try:
        print(f"🔄 Background RAG indexing started for {thread_id}")
        indexed_count = index_all_candidates_for_thread(thread_id)
        print(f"✅ RAG indexing complete: {indexed_count} candidates indexed")
    except Exception as e:
        print(f"⚠️ RAG indexing error: {e}")

def screening_node(state: ApplicationState) -> ApplicationState:
    """CV screening node"""
    
    print("🔍 Screening node - processing CVs...")
    
    thread_id = state.get("thread_id")
    job_description = state.get("job_description")
    num_cvs = state.get("retrieved_n_cvs", 20)
    
    # Validation
    if not job_description:
        state["response_message"] = "<p>❌ Job description not available for this position.</p>"
        return state
    
    if not state.get("cvs_available"):
        state["response_message"] = "<p>❌ No CVs uploaded yet. Please upload CVs first.</p>"
        return state
    
    try:
        # Screen CVs
        df = screen_cvs(job_description, num_cvs, thread_id, max_workers=3)
        
        if df.empty:
            state["response_message"] = "<p>❌ No candidates could be processed.</p>"
            return state
        
        # Sort by score
        if "score" in df.columns:
            df = df.astype({"score": float}).sort_values("score", ascending=False)
        
        # Remove internal columns
        drop_cols = ["cv_path", "thread_id", "job_desc", "status"]
        df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
        
        # Generate HTML table
        html_table = dataframe_to_html(df)
        
        state["response_message"] = f"""
        {html_table}
        
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #0066cc;">
            <h3 style="margin-top: 0; font-size: 16px;">📊 Screening Complete</h3>
            <p style="margin: 10px 0;"><strong>Total Candidates:</strong> {len(df)}</p>
            <p style="margin: 10px 0;">💡 <strong>Tip:</strong> Ask questions like "why did candidate X score higher than Y?" or "show me candidates with Python experience"</p>
        </div>
        """
        
        state["screening_complete"] = True
        state["screening_results"] = df.to_dict('records')
        
        # Launch background RAG indexing
        rag_thread = threading.Thread(
            target=background_rag_indexing,
            args=(thread_id,),
            daemon=True
        )
        rag_thread.start()
        
        print(f"✅ Screening complete: {len(df)} candidates")
        
    except Exception as e:
        state["response_message"] = f"<p>❌ Error during screening: {str(e)}</p>"
        print(f"❌ Screening error: {e}")
        import traceback
        traceback.print_exc()
    
    return state