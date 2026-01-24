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
            state["response_json"] = {"error": "No candidates match your search criteria."}
            state["response_message"] = "No candidates match your search criteria."
            return state
        # Create dataframe
        df = pd.DataFrame(results, columns=columns)
        # Sort by score if available
        if "score" in df.columns:
            df = df.astype({"score": float}).sort_values("score", ascending=False)
        # Drop internal columns
        drop_cols = ["cv_path", "thread_id", "job_desc", "status"]
        df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
        # Return as JSON
        state["response_json"] = {
            "total_results": len(df),
            "results": df.to_dict('records')
        }
        # Format message for frontend
        state["response_message"] = f"Found {len(df)} candidates matching your criteria.\n\nTop results:\n" + "\n".join([f"- {row.get('english_name', 'Unknown')}: Score {row.get('score', 'N/A')}" for row in df.head(5).to_dict('records')])
        print(f"✅ Query executed: {len(results)} results")
    except Exception as e:
        state["response_json"] = {"error": f"Error executing query: {str(e)}"}
        state["response_message"] = f"Error executing query: {str(e)}"
        print(f"❌ SQL error: {e}")
    return state