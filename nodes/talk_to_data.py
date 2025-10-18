import pandas as pd
from models.state import ApplicationState
from utils.sql_generator import generate_sql_query
from utils.html_formatter import dataframe_to_html
from database.schema import execute_sql_query

def talk_to_data_node(state: ApplicationState) -> ApplicationState:
    """SQL query handler node"""
    
    print("📊 Talk to data node...")
    
    user_input = state.get("user_input", "")
    thread_id = state.get("thread_id")
    
    try:
        # Generate SQL
        sql_query = generate_sql_query(user_input, thread_id)
        
        # Execute query
        results, columns = execute_sql_query(sql_query)
        
        if len(results) == 0:
            state["response_message"] = """
            <div style="text-align: center; padding: 40px; font-family: Arial, sans-serif;">
                <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 30px; display: inline-block;">
                    <h3 style="color: #495057; margin: 10px 0;">🔍 No Results Found</h3>
                    <p style="color: #6c757d; margin: 5px 0;">No candidates match your search criteria.</p>
                </div>
            </div>
            """
            return state
        
        # Create dataframe
        df = pd.DataFrame(results, columns=columns)
        
        # Sort by score if available
        if "score" in df.columns:
            df = df.astype({"score": float}).sort_values("score", ascending=False)
        
        # Drop internal columns
        drop_cols = ["cv_path", "thread_id", "job_desc", "status"]
        df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
        
        # Generate HTML
        html_table = dataframe_to_html(df)
        
        state["response_message"] = html_table
        print(f"✅ Query executed: {len(results)} results")
        
    except Exception as e:
        state["response_message"] = f"<p>❌ Error executing query: {str(e)}</p>"
        print(f"❌ SQL error: {e}")
    
    return state