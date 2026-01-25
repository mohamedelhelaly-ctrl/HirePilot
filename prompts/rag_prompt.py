def get_rag_prompt(user_query: str, context: str, job_object: dict) -> str:
    """RAG explanation prompt"""
    
    # Format job information
    job_info = "Not provided"
    if job_object:
        parts = []
        if job_object.get("title"):
            parts.append(f"Position: {job_object['title']}")
        if job_object.get("location"):
            parts.append(f"Location: {job_object['location']}")
        if job_object.get("level"):
            parts.append(f"Employment Level: {job_object['level']}")
        if job_object.get("description"):
            parts.append(f"\nDescription:\n{job_object['description']}")
        if job_object.get("requirements"):
            reqs = job_object['requirements']
            if isinstance(reqs, list):
                parts.append(f"\nKey Requirements:\n" + "\n".join([f"- {req}" for req in reqs]))
            else:
                parts.append(f"\nRequirements: {reqs}")
        if job_object.get("details"):
            parts.append(f"\nFull Details:\n{job_object['details']}")
        job_info = "\n".join(parts)
    
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

Job Information:
{job_info}

Candidate Information:
{context}

Recruiter's Question:
{user_query}

Provide detailed analysis in plain text with markdown formatting (no HTML):"""
    
    return prompt