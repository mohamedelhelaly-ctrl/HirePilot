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
            kw_lower = keyword.lower()
            escaped_kw = re.escape(kw_lower)

            if re.search(r'[^\w\s]', keyword):
                pattern = rf'(?:^|\s){escaped_kw}(?:\s|$)'
            else:
                pattern = rf'\b{escaped_kw}\b'

            matches = re.findall(pattern, text)
            found = len(matches) > 0
            found_map[keyword] = found

            if found:
                found_count += 1

        if len(keywords) == 0:
            ratio = 1.0
            section_passed = True
        else:
            ratio = found_count / len(keywords)
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

                updated_metadatas = []
                for doc_id in doc_ids:
                    try:
                        existing_docs = vector_index.get(ids=[doc_id])
                        if existing_docs and "metadatas" in existing_docs and existing_docs["metadatas"]:
                            existing_metadata = existing_docs["metadatas"][0]
                            updated_metadata = {**existing_metadata, "filtered": cv_passed}
                            updated_metadatas.append(updated_metadata)
                        else:
                            updated_metadatas.append({
                                "source": filename,
                                "thread_id": thread_id,
                                "filtered": cv_passed
                            })
                    except Exception:
                        continue

                if updated_metadatas and len(updated_metadatas) == len(doc_ids):
                    try:
                        vector_index._collection.update(
                            ids=doc_ids,
                            metadatas=updated_metadatas
                        )
                    except Exception:
                        for doc_id, metadata in zip(doc_ids, updated_metadatas):
                            try:
                                vector_index._collection.update(
                                    ids=[doc_id],
                                    metadatas=[metadata]
                                )
                            except Exception:
                                pass
        except Exception:
            pass

    try:
        if hasattr(vector_index, 'persist'):
            vector_index.persist()
        elif hasattr(vector_index, '_client'):
            vector_index._client.persist()
    except Exception:
        pass

    return {
        "passed": passed_cvs,
        "failed": failed_cvs,
        "total": len(pdf_files)
    }
