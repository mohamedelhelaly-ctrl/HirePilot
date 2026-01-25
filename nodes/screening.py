import threading
from models.state import ApplicationState
from utils.screening_engine import screen_cvs
from utils.html_formatter import dataframe_to_html
from utils.rag_retrieval import index_all_candidates_for_thread
import json
import os
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
    job_object = state.get("job_object")
    job_description = state.get("job_description")
    
    # If job_object is not provided, load from jobs.json
    if not job_object:
        jobs_path = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.json")
        try:
            with open(jobs_path, "r", encoding="utf-8") as f:
                jobs = json.load(f)
            job_object = next((j for j in jobs if j["id"] == thread_id), None)
            if job_object:
                state["job_object"] = job_object
                job_description = job_object.get("details") or job_object.get("description")
                state["job_description"] = job_description
        except Exception as e:
            print(f"Error loading job from jobs.json: {e}")
            state["response_json"] = {"error": "Job information not available."}
            state["response_message"] = "Job information not available."
            return state
    
    num_cvs = state.get("retrieved_n_cvs", 20)
    
    # Validation
    if not job_description:
        state["response_json"] = {"error": "Job description not available for this position."}
        state["response_message"] = "Job description not available for this position."
        return state
    if not state.get("cvs_available"):
        state["response_json"] = {"error": "No CVs uploaded yet. Please upload CVs first."}
        state["response_message"] = "No CVs uploaded yet. Please upload CVs first."
        return state
    
    try:
        # Screen CVs
        df = screen_cvs(job_description, num_cvs, thread_id, max_workers=3)
        
        if df.empty:
            state["response_json"] = {"error": "No candidates could be processed."}
            state["response_message"] = "No candidates could be processed."
            return state
        
        # Sort by score
        if "score" in df.columns:
            df = df.astype({"score": float}).sort_values("score", ascending=False)
        # Remove internal columns
        drop_cols = ["cv_path", "thread_id", "job_desc", "status"]
        df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
        # Prepare JSON response
        state["response_json"] = {
            "total_candidates": len(df),
            "candidates": df.to_dict('records'),
            "screening_complete": True,
            "tip": "Ask questions like 'why did candidate X score higher than Y?' or 'show me candidates with Python experience'"
        }
        state["screening_complete"] = True
        state["screening_results"] = df.to_dict('records')
        
        # Format message for frontend
        state["response_message"] = f"✅ Screening complete! Processed {len(df)} candidates.\n\nTop 5 candidates:\n" + "\n".join([f"{i+1}. {row.get('english_name', 'Unknown')} - Score: {row.get('score', 'N/A')}%" for i, row in enumerate(df.head(5).to_dict('records'))])
        
        # Launch background RAG indexing
        rag_thread = threading.Thread(
            target=background_rag_indexing,
            args=(thread_id,),
            daemon=True
        )
        rag_thread.start()
        
        print(f"✅ Screening complete: {len(df)} candidates")
    except Exception as e:
        state["response_json"] = {"error": f"Error during screening: {str(e)}"}
        state["response_message"] = f"Error during screening: {str(e)}"
        print(f"❌ Screening error: {e}")
        import traceback
        traceback.print_exc()
    return state