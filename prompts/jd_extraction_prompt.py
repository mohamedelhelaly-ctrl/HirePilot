import json

def get_jd_extraction_prompt(job_description: str, schema: dict) -> str:
    """Job description entity extraction prompt"""
    
    prompt = f"""Extract key entities from this job description.

Return ONLY valid JSON matching this schema:
{{
  "job_title": "Senior AI/ML Engineer",
  "years_of_experience": "5+",
  "required_skills": ["Python", "TensorFlow", "Machine Learning"],
  "required_education": "Bachelor's in Computer Science",
  "location": "Cairo",
  "languages": ["English"],
  "soft_skills": ["Communication", "Collaboration"],
  "certifications": []
}}

**Rules:**
- For years_of_experience: use format "5+", "3-5", "0-2", etc.
- Extract ALL technical skills mentioned
- If not specified, use empty array []

Schema:
{json.dumps(schema, indent=2)}

Job Description:
{job_description}

Return ONLY the JSON:"""
    
    return prompt