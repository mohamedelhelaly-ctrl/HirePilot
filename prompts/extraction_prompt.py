import json
from datetime import datetime

def get_extraction_prompt(cv_text: str, job_description: str, jd_entities: dict, schema: dict) -> str:
    """
    CV data extraction prompt - LLM extracts ALL work history, Python handles filtering
    """
    
    current_date = datetime.now().strftime("%B %Y")
    current_month_year = datetime.now().strftime("%b %Y")
    current_numeric = datetime.now().strftime("%m/%Y")
    
    jd_experience = jd_entities.get("years_of_experience", "0-2")
    
    prompt = f"""Extract structured data from the CV and calculate a match score against the job description.

### DATABASE SCHEMA
Output must match these fields:
- english_name: TEXT
- graduation_year: INTEGER (e.g., 2020)
- nationality: TEXT
- gender: TEXT
- email: TEXT
- phone_number: TEXT
- current_city: TEXT
- years_of_experience: INTEGER (will be recalculated by system)
- study_field: TEXT
- universities: JSON array
- soft_skills: JSON array
- technical_skills: JSON array
- Certifications: JSON array
- Languages: JSON array
- linkedin_url: TEXT
- score: TEXT (float as string, e.g., "75.5")
- justification: TEXT (one sentence, max 20 words)

### CRITICAL INSTRUCTIONS

**1. WORK HISTORY EXTRACTION**

Extract ALL work experience entries from the CV - do not filter anything.

**Required format:**
```json
[
  {{
    "role": "Senior Software Engineer",
    "company": "TechCorp",
    "start_date": "3/2024",
    "end_date": "Present"
  }},
  {{
    "role": "ML Intern",
    "company": "StartUp AI",
    "start_date": "6/2023",
    "end_date": "12/2023"
  }},
  {{
    "role": "Teaching Assistant",
    "company": "University",
    "start_date": "9/2021",
    "end_date": "6/2022"
  }}
]
```

**Extraction rules:**
- Include EVERY job/role mentioned in CV (internships, full-time, part-time, freelance, volunteer, etc.)
- Preserve EXACT date formats from CV: "3/2024", "Mar 2024", "March 2024", "11/2022", "Sept 2024"
- For ongoing roles: use "Present" (even if CV says "Current", "Now", "Ongoing")
- Do NOT skip or filter any roles - extract everything
- If no work history exists: return empty array `[]`

Current date for reference: **{current_date}** ({current_month_year} or {current_numeric})

---

**2. TECHNICAL SKILLS EXTRACTION**

Extract ALL technical skills found anywhere in the CV:
- Skills section
- Technologies mentioned in job descriptions
- Tools used in projects
- Programming languages
- Frameworks, libraries, platforms, databases, cloud services

**Aim for 15-25 skills if available in CV**

Examples: ["Python", "JavaScript", "TensorFlow", "React", "Docker", "AWS", "PostgreSQL", "Git"]

---

**3. MATCH SCORE CALCULATION (0-100)**

Calculate an accurate score based on job requirements: {jd_experience} years experience

**Technical Skills Match (40 points):**
- Compare CV technical skills vs JD required skills
- Formula: (matching_skills / required_skills) × 40
- Example: 8 out of 10 required = 32 points
- Bonus: Extra highly relevant skills can add up to +5 points

**Experience Match (25 points):**
- Within required range: 25 points
- 1 year under/over: 18 points
- 2+ years under: 8 points
- Fresh graduate for senior role (3+ years): 0 points
- Significantly over-qualified: 15 points

**Education Match (15 points):**
- Exact degree match (CS for AI role): 15 points
- Related field (Engineering, Math, Data Science): 10 points
- Unrelated but strong technical skills: 5 points
- No degree or completely unrelated: 0 points

**Certifications (10 points):**
- Highly relevant certifications: 10 points
- Somewhat relevant: 6 points
- Generic or outdated: 2 points
- None: 0 points

**Soft Skills & Fit (10 points):**
- Strong evidence of required soft skills: 10 points
- Some evidence: 6 points
- Minimal evidence: 2 points

**Score range:** 0-100 (be specific, avoid generic scores like 50, 60, 70)
**Examples:** 34.0, 58.5, 72.0, 84.5, 91.0

---

**4. JUSTIFICATION**

Write ONE concise sentence (max 20 words) explaining the score.

**Good examples:**
- "Strong Python and ML skills with 3 years experience but lacks AWS certification"
- "Perfect fit with 5 years AI experience and all required technical skills"
- "Under-qualified with only 6 months internship and missing key frameworks"
- "Excellent skills but over-qualified with 10 years for junior role"

**Bad examples (avoid):**
- "Good candidate" (too vague)
- "Has some experience in the field and decent skills" (too generic)
- Long explanations with multiple sentences

---

### OUTPUT FORMAT

Return ONLY valid JSON (no text before or after):

```json
{{
  "english_name": "Ahmed Mohamed",
  "graduation_year": 2020,
  "nationality": "Egyptian",
  "gender": "Male",
  "email": "ahmed@example.com",
  "phone_number": "+201234567890",
  "current_city": "Cairo, Egypt",
  "linkedin_url": "linkedin.com/in/ahmedm",
  "years_of_experience": 0,
  "study_field": "Computer Science",
  "universities": ["Cairo University"],
  "work_history": [
    {{
      "role": "AI Engineer",
      "company": "TechCorp",
      "start_date": "3/2024",
      "end_date": "Present"
    }},
    {{
      "role": "ML Intern",
      "company": "StartUp",
      "start_date": "6/2023",
      "end_date": "12/2023"
    }}
  ],
  "technical_skills": ["Python", "TensorFlow", "PyTorch", "Docker", "AWS", "SQL", "Git"],
  "soft_skills": ["Communication", "Problem Solving", "Teamwork"],
  "Languages": ["English", "Arabic"],
  "Certifications": ["AWS ML Specialty"],
  "score": "76.5",
  "justification": "Strong ML skills with relevant experience but lacks some certifications"
}}
```

**VALIDATION RULES:**
1. Output ONLY JSON - no explanations or comments
2. `work_history` must be complete array of ALL roles found
3. `years_of_experience` can be 0 (will be recalculated by system)
4. `graduation_year` must be INTEGER
5. `score` must be TEXT containing float (e.g., "75.5")
6. `justification` must be ONE sentence max 20 words
7. Arrays must be valid JSON arrays
8. Empty fields: use "" or []
9. Current date is {current_numeric}

Job Description Requirements:
{json.dumps(jd_entities, indent=2)}

Job Description:
{job_description}

CV Text:
{cv_text}

Return ONLY the JSON:"""
    
    return prompt