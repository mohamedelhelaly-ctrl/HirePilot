import os
import re
import fitz
from typing import Dict, List

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF"""
    text = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text.append(page.get_text("text"))
    return "\n".join(text).lower()

def check_keywords_in_cv(pdf_path: str, filter_config: Dict[str, Dict]) -> Dict:
    """Check if CV passes keyword filters"""
    
    text = extract_text_from_pdf(pdf_path)
    
    results = {
        "cv_filename": pdf_path,
        "overall_passed": True,
        "sections": {}
    }
    
    for section_name, config in filter_config.items():
        keywords = config["keywords"]
        required_ratio = config.get("required_ratio", 1.0)
        
        found_count = 0
        found_map = {}
        
        for keyword in keywords:
            escaped_kw = re.escape(keyword)
            
            # Handle special characters in keywords
            if re.search(r'[^\w\s]', keyword):
                pattern = rf'(?:^|\s){escaped_kw}(?:\s|$)'
            else:
                pattern = rf'\b{escaped_kw}\b'
            
            matches = re.findall(pattern, text, re.IGNORECASE)
            found = len(matches) > 0
            found_map[keyword] = found
            
            if found:
                found_count += 1
        
        ratio = found_count / len(keywords) if len(keywords) > 0 else 0
        section_passed = ratio >= required_ratio
        
        results["sections"][section_name] = {
            "keywords": found_map,
            "found_count": found_count,
            "total_keywords": len(keywords),
            "ratio": round(ratio, 2),
            "required_ratio": required_ratio,
            "passed": section_passed
        }
        
        if not section_passed:
            results["overall_passed"] = False
    
    return results

def apply_initial_filter(thread_id: str, filter_config: Dict, vector_index) -> Dict:
    """Apply initial keyword filter to all CVs for a thread"""
    
    cvs_dir = f"assets/cvs/{thread_id}"
    
    if not os.path.exists(cvs_dir):
        return {"passed": [], "failed": [], "error": "CV directory not found"}
    
    pdf_files = [f for f in os.listdir(cvs_dir) if f.lower().endswith(".pdf")]
    
    passed_cvs = []
    failed_cvs = []
    
    for filename in pdf_files:
        file_path = os.path.join(cvs_dir, filename)
        result = check_keywords_in_cv(file_path, filter_config)
        
        cv_passed = result["overall_passed"]
        
        if cv_passed:
            passed_cvs.append(filename)
        else:
            failed_cvs.append(filename)
        
        # Update vector database metadata
        try:
            docs = vector_index.get(
                where={
                    "$and": [
                        {"source": {"$eq": filename}},
                        {"thread_id": {"$eq": thread_id}}
                    ]
                }
            )
            
            if docs and "ids" in docs and docs["ids"]:
                doc_ids = docs["ids"]
                
                # Update all chunks for this CV
                for doc_id in doc_ids:
                    existing_docs = vector_index.get(ids=[doc_id])
                    if existing_docs and "metadatas" in existing_docs:
                        existing_metadata = existing_docs["metadatas"][0]
                        updated_metadata = {**existing_metadata, "filtered": cv_passed}
                        
                        vector_index._collection.update(
                            ids=[doc_id],
                            metadatas=[updated_metadata]
                        )
        except Exception as e:
            print(f"⚠️ Error updating vector DB for {filename}: {e}")
    
    return {
        "passed": passed_cvs,
        "failed": failed_cvs,
        "total": len(pdf_files)
    }