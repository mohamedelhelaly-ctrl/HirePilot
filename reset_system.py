"""
System Reset Script
Resets the Incorta HR system to initial state by:
- Clearing all CVs from assets/cvs
- Resetting jobs.json to empty array
- Clearing conversation history
- Clearing vector index store
- Resetting candidates database
"""

import os
import json
import shutil
import sqlite3

def reset_cvs():
    """Delete all CV directories inside assets/cvs"""
    cvs_dir = "assets/cvs"
    if os.path.exists(cvs_dir):
        for item in os.listdir(cvs_dir):
            item_path = os.path.join(cvs_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"✅ Deleted CV directory: {item}")
    print("✅ CVs cleared")

def reset_jobs():
    """Reset jobs.json to empty array"""
    jobs_path = "data/jobs.json"
    with open(jobs_path, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    print("✅ Jobs.json reset to empty array")

def reset_conversations():
    """Delete all conversation JSON files"""
    conv_dir = "database/store/conversations"
    if os.path.exists(conv_dir):
        for file in os.listdir(conv_dir):
            if file.endswith(".json"):
                file_path = os.path.join(conv_dir, file)
                os.remove(file_path)
                print(f"✅ Deleted conversation: {file}")
    print("✅ Conversations cleared")

def reset_index_store():
    """Clear vector index store"""
    index_dir = "database/store/index_store"
    if os.path.exists(index_dir):
        for item in os.listdir(index_dir):
            item_path = os.path.join(index_dir, item)
            # Keep chroma.sqlite3 but reset it, delete UUID folders
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"✅ Deleted index: {item}")
            elif item == "chroma.sqlite3":
                # Delete and recreate empty
                os.remove(item_path)
                print(f"✅ Reset chroma.sqlite3")
    print("✅ Index store cleared")

def reset_candidates_db():
    """Reset candidates database"""
    db_path = "database/store/candidates.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Delete all candidates
        cursor.execute("DELETE FROM candidates")
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        print(f"✅ Deleted {deleted} candidates from database")
    else:
        print("⚠️ Candidates database not found")

def main():
    """Main reset function"""
    print("\n" + "="*60)
    print("🔄 SYSTEM RESET - Incorta HR Agent")
    print("="*60 + "\n")
    
    confirm = input("⚠️ This will DELETE all CVs, jobs, conversations, and candidates. Continue? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("❌ Reset cancelled")
        return
    
    print("\n🔄 Starting reset...\n")
    
    try:
        reset_cvs()
        reset_jobs()
        reset_conversations()
        reset_index_store()
        reset_candidates_db()
        
        print("\n" + "="*60)
        print("✅ SYSTEM RESET COMPLETE")
        print("="*60)
        print("\nThe system is now in initial state.")
        print("You can create new jobs from the frontend.\n")
        
    except Exception as e:
        print(f"\n❌ Error during reset: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
