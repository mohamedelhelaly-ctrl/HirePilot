import sqlite3
import json
from config.database_config import get_db_connection, TABLE_NAME

def get_table_columns(table_name=TABLE_NAME):
    """Return list of column names for the table"""
    conn = get_db_connection()
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    return columns

def get_sqlite_schema():
    """Generate schema with column names, types, and sample values"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns_info = cursor.fetchall()
    
    columns = [col[1] for col in columns_info]
    dtypes = {col[1]: col[2] for col in columns_info}
    
    sample_values = {}
    for col in columns:
        try:
            cursor = conn.execute(f"SELECT {col} FROM {TABLE_NAME} WHERE {col} IS NOT NULL LIMIT 1")
            result = cursor.fetchone()
            sample_values[col] = str(result[0]) if result else "None"
        except sqlite3.Error:
            sample_values[col] = "None"
    
    conn.close()
    
    schema = {
        TABLE_NAME: {
            "dtypes": dtypes,
            "sample_values": sample_values
        }
    }
    
    return json.dumps(schema, indent=2, ensure_ascii=False)

def execute_sql_query(query: str):
    """Execute SELECT query and return results"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return results, columns

def candidate_exists(cv_path: str, thread_id: str) -> bool:
    """Check if candidate exists in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT 1 FROM {TABLE_NAME} WHERE cv_path = ? AND thread_id = ? LIMIT 1",
        (cv_path.strip(), thread_id.strip())
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def insert_candidate(candidate_dict: dict):
    """Insert candidate into database"""
    conn = get_db_connection()
    columns = ', '.join(candidate_dict.keys())
    placeholders = ', '.join(['?'] * len(candidate_dict))
    sql = f"INSERT INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})"
    values = list(candidate_dict.values())
    conn.execute(sql, values)
    conn.commit()
    conn.close()

def fetch_candidate_by_path(cv_path: str, thread_id: str):
    """Fetch candidate info by cv_path and thread_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    columns = get_table_columns()
    
    column_list = ', '.join(columns)
    cursor.execute(
        f"SELECT {column_list} FROM {TABLE_NAME} WHERE cv_path = ? AND thread_id = ? LIMIT 1",
        (cv_path, thread_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = dict(zip(columns, row))
    
    # Parse JSON fields
    for key in ['universities', 'soft_skills', 'technical_skills', 'Certifications', 'Languages']:
        if key in result and result[key]:
            try:
                result[key] = json.loads(result[key])
            except:
                pass
    
    return result