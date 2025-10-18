import re
from config.llm_config import llm_sql
from prompts.sql_prompt import get_sql_prompt
from database.schema import get_sqlite_schema

def clean_sql_query(sql_query: str) -> str:
    """Clean SQL response from LLM"""
    
    # Remove markdown code blocks
    sql_query = re.sub(r'```sql\n?', '', sql_query)
    sql_query = re.sub(r'```\n?', '', sql_query)
    
    # Remove trailing semicolon
    sql_query = sql_query.strip().rstrip(';')
    
    # Get first SELECT statement
    lines = sql_query.split('\n')
    sql_lines = [line for line in lines if line.strip().upper().startswith('SELECT')]
    
    if sql_lines:
        sql_query = sql_lines[0]
    
    return sql_query.strip()

def generate_sql_query(question: str, thread_id: str) -> str:
    """Convert natural language to SQL query"""
    
    schema = get_sqlite_schema()
    prompt = get_sql_prompt(schema, question, thread_id)
    
    response = llm_sql.generate(prompt)
    sql_query = response['results'][0]['generated_text']
    
    cleaned_query = clean_sql_query(sql_query)
    
    print(f"🔍 Generated SQL: {cleaned_query}")
    return cleaned_query