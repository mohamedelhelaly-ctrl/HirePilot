import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from config.vector_config import get_vector_index
from database.schema import candidate_exists, insert_candidate, fetch_candidate_by_path, get_table_columns
from utils.cv_extraction import extract_cv_data

def process_single_cv(filename: str, cvs_dir: str, job_description: str, 
                     thread_id: str, columns: list) -> dict:
    """Process a single CV"""
    
    try:
        cv_path = os.path.join(cvs_dir, filename)
        thread_cv_path = f"assets/cvs/{thread_id}/{filename}"
        
        if not candidate_exists(thread_cv_path, thread_id):
            # Extract CV data (includes Python-side experience calculation)
            extracted_data = extract_cv_data(cv_path, job_description)
            
            if not extracted_data or all(v == "" for v in extracted_data.values()):
                return None
            
            # Update paths
            extracted_data["cv_path"] = thread_cv_path
            extracted_data["thread_id"] = thread_id
            extracted_data["job_desc"] = job_description
            
            return {
                "action": "insert",
                "data": extracted_data,
                "path": thread_cv_path
            }
        else:
            return {
                "action": "fetch",
                "path": thread_cv_path
            }
    
    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")
        return None


def screen_cvs(job_description: str, num_cvs: int, thread_id: str, max_workers: int = 1) -> pd.DataFrame:
    """Screen CVs against job description"""
    
    print(f'🚀 Screening {num_cvs} CVs for thread {thread_id}')
    
    vector_index = None
    
    try:
        columns = get_table_columns()
        if "candidate_id" in columns:
            columns.remove("candidate_id")
        
        # Get vector index
        vector_index = get_vector_index()
        
        # Similarity search
        search_results = vector_index.similarity_search_with_relevance_scores(
            job_description,
            k=num_cvs * 5,
            filter={
                "$and": [
                    {"thread_id": {"$eq": thread_id}},
                    {"filtered": {"$eq": True}}
                ]
            }
        )

        # Normalize scores to [0, 1]
        search_results = [
            (doc, max(0.0, min(1.0, abs(score)))) for doc, score in search_results
        ]

        # Sort by score descending
        search_results.sort(key=lambda x: x[1], reverse=True)

        print(f"📊 Found {len(search_results)} document chunks")
        
        # Get unique CVs
        seen_files = set()
        unique_docs = []
        
        for doc, score in search_results:
            if len(unique_docs) >= num_cvs:
                break
            
            filename = os.path.basename(doc.metadata.get("source", ""))
            if filename not in seen_files:
                seen_files.add(filename)
                unique_docs.append((doc, score))
        
        print(f"🔄 Processing {len(unique_docs)} unique CVs...")
        
        cvs_dir = f"assets/cvs/{thread_id}"
        new_candidates = []
        fetch_paths = []
        
        # Process CVs (with experience calculation)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    process_single_cv,
                    os.path.basename(doc.metadata.get("source")),
                    cvs_dir,
                    job_description,
                    thread_id,
                    columns
                )
                for doc, score in unique_docs
            ]
            
            for future in futures:
                result = future.result()
                if result:
                    if result["action"] == "insert":
                        new_candidates.append(result["data"])
                    elif result["action"] == "fetch":
                        fetch_paths.append(result["path"])
        
        # Insert new candidates
        if new_candidates:
            print(f"💾 Inserting {len(new_candidates)} new candidates...")
            for candidate in new_candidates:
                try:
                    insert_candidate(candidate)
                except Exception as e:
                    print(f"❌ Error inserting candidate: {e}")
        
        # Fetch all candidates
        response = []
        all_paths = fetch_paths + [c["cv_path"] for c in new_candidates]
        
        for path in all_paths:
            candidate_info = fetch_candidate_by_path(path, thread_id)
            if candidate_info:
                response.append(candidate_info)
        
        print(f"✅ Screening complete: {len(response)} candidates processed")
        return pd.DataFrame(response)
    
    except Exception as e:
        print(f"❌ Error in screening: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    
    finally:
        if vector_index:
            del vector_index