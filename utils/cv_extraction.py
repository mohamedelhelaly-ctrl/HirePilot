import json
from json_repair import repair_json
from config.llm_config import llm_extraction
from prompts.extraction_prompt import get_extraction_prompt
from prompts.jd_extraction_prompt import get_jd_extraction_prompt
from models.cv_schema import CVDetails
from models.jd_schema import JDDetails
from utils.cv_text_parser import extract_text_from_pdf
from utils.experience_calculator import calculate_total_experience
from database.schema import get_table_columns

def extract_cv_data(cv_path: str, job_description: str) -> dict:
    """Extract structured data from CV with Python-side experience calculation"""
    
    columns = get_table_columns()
    if "candidate_id" in columns:
        columns.remove("candidate_id")
    
    empty_result = {k: "" for k in columns}
    
    try:
        # Extract text from PDF
        extraction_result = extract_text_from_pdf(cv_path)
        cv_text = extraction_result.get("text", "")
        linkedin_url = extraction_result.get("linkedin")
        
        if not cv_text.strip():
            print(f"❌ No text extracted from {cv_path}")
            return empty_result
        
        print(f"📄 Processing: {cv_path}")
        
        # Extract JD entities
        jd_schema = json.dumps(JDDetails.model_json_schema(), indent=2)
        jd_prompt = get_jd_extraction_prompt(job_description, jd_schema)
        jd_response = llm_extraction.generate(jd_prompt)
        jd_text = jd_response['results'][0]['generated_text']
        jd_repaired = repair_json(jd_text, ensure_ascii=False)
        jd_entities = json.loads(jd_repaired)
        
        # Extract CV data
        cv_schema = json.dumps(CVDetails.model_json_schema(), indent=2)
        cv_prompt = get_extraction_prompt(cv_text, job_description, jd_entities, cv_schema)
        cv_response = llm_extraction.generate(cv_prompt)
        cv_extracted_text = cv_response['results'][0]['generated_text']
        
        if not cv_extracted_text.strip():
            print("❌ Empty response from LLM")
            return empty_result
        
        cv_repaired = repair_json(cv_extracted_text, ensure_ascii=False)
        extracted_data = json.loads(cv_repaired)
        
        # ✅ PYTHON-SIDE EXPERIENCE CALCULATION
        work_history = extracted_data.get("work_history", [])
        
        if work_history and isinstance(work_history, list):
            # Recalculate experience using Python logic
            calculated_experience = calculate_total_experience(work_history)
            extracted_data['years_of_experience'] = calculated_experience
            
            print(f"   📊 Work history: {len(work_history)} total roles")
            print(f"   ✅ Calculated experience: {calculated_experience} years")
        else:
            extracted_data['years_of_experience'] = 0
            print(f"   ⚠️ No work history found, experience set to 0")
        
        # Add LinkedIn if found
        if linkedin_url:
            extracted_data['linkedin_url'] = linkedin_url
        
        # Set default status
        extracted_data['status'] = 'pending'
        
        # Convert to DB format
        processed_data = {}
        for k, v in extracted_data.items():
            if isinstance(v, (list, dict)):
                processed_data[k] = json.dumps(v, ensure_ascii=False)
            elif v is not None:
                processed_data[k] = str(v)
            else:
                processed_data[k] = ""
        
        result = {col: processed_data.get(col, "") for col in columns}
        
        score = extracted_data.get('score', '0')
        print(f"   📈 Score: {score}")
        
        return result
    
    except Exception as e:
        print(f"❌ Error extracting CV data: {e}")
        import traceback
        traceback.print_exc()
        return empty_result
