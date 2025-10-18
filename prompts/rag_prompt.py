def get_rag_prompt(user_query: str, context: str, job_description: str) -> str:
    """RAG explanation prompt"""
    
    prompt = f"""You are an expert recruitment analyst. Analyze the candidate information and answer the recruiter's question.

Guidelines:
1. Be specific - cite candidate IDs and names
2. Use professional, clear language
3. Structure response with clear sections (use ### for headers)
4. For skills, use comma-separated format: "Python, SQL, Java"
5. Provide concrete examples from CVs
6. If asked about scores, reference the quantitative data
7. End with a brief conclusion (2-3 sentences)
8. ONLY discuss candidates whose information is provided below

Job Requirements:
{job_description if job_description else "Not provided"}

Candidate Information:
{context}

Recruiter's Question:
{user_query}

Provide detailed analysis in plain text with markdown formatting (no HTML):"""
    
    return prompt