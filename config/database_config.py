import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "database/store/candidates.db")
TABLE_NAME = os.getenv("TABLE_NAME", "candidates")

CANDIDATES_SCHEMA = {
    'cv_path': 'TEXT',
    'english_name': 'TEXT',
    'graduation_year': 'INTEGER',
    'nationality': 'TEXT',
    'email': 'TEXT',
    'phone_number': 'TEXT',
    'current_city': 'TEXT',
    'years_of_experience': 'INTEGER',
    'study_field': 'TEXT',
    'universities': 'TEXT',
    'soft_skills': 'TEXT',
    'technical_skills': 'TEXT',
    'Certifications': 'TEXT',
    'Languages': 'TEXT',
    'linkedin_url': 'TEXT',
    'job_desc': 'TEXT',
    'score': 'TEXT',
    'justification': 'TEXT',
    'status': 'TEXT',
    'thread_id': 'TEXT'
}

def get_db_connection(db_path=DB_PATH):
    """Create and return SQLite connection"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def initialize_database():
    """Initialize candidates database with schema"""
    # Check if database file exists
    db_exists = os.path.exists(DB_PATH)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(f"""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='{TABLE_NAME}'
    """)
    table_exists = cursor.fetchone() is not None
    
    # Create table if it doesn't exist
    if not table_exists:
        columns_sql = ", ".join([f"{col} {col_type}" for col, col_type in CANDIDATES_SCHEMA.items()])
        cursor.execute(f"""
            CREATE TABLE {TABLE_NAME} (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns_sql}
            )
        """)
        conn.commit()
        print(f"✅ Database initialized at {DB_PATH}")
    else:
        print(f"✅ Database connected at {DB_PATH}")
    
    conn.close()