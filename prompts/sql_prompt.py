def get_sql_prompt(schema: str, question: str, thread_id: str) -> str:
    """Text-to-SQL prompt"""
    
    prompt = f"""You are an expert SQL query generator.

Convert the natural language question to a valid SQLite SELECT statement.

**Rules:**
1. ALWAYS include: WHERE thread_id = '{thread_id}'
2. Output ONLY the SQL query (no explanation, no markdown)
3. Use only columns from the schema
4. Never use DELETE, UPDATE, or INSERT
5. For "candidate X" use: WHERE candidate_id = X

**Schema:**
{schema}

**Examples:**

Q: show candidates over 5 years experience
A: SELECT * FROM candidates WHERE thread_id = '{thread_id}' AND years_of_experience > 5

Q: list top 10 by score
A: SELECT * FROM candidates WHERE thread_id = '{thread_id}' ORDER BY CAST(score AS REAL) DESC LIMIT 10

Q: show candidate 5
A: SELECT * FROM candidates WHERE thread_id = '{thread_id}' AND candidate_id = 5

**Question:** {question}

SQL query:"""
    
    return prompt