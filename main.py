import os
import uuid
import json
import re
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from config.database_config import initialize_database, get_db_connection
from config.vector_config import get_vector_index
from utils.cv_processing import process_and_vectorize_cv
from utils.initial_filter import apply_initial_filter
from graph import run_workflow
from database.schema import execute_sql_query, fetch_candidate_by_path
from models.conversation import ConversationStore

# Initialize FastAPI
app = FastAPI(title="Incorta Recruitment Demo")

# Mount static files directory for serving logo
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    initialize_database()
    print("✅ Application started")

# Request model
class ChatRequest(BaseModel):
    user_message: str
    thread_id: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint (returns structured JSON)"""
    user_message = request.user_message
    thread_id = request.thread_id
    if not user_message or not user_message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Load full job object from jobs.json
    job_object = None
    jobs_path = os.path.join("data", "jobs.json")
    try:
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        job_object = next((j for j in jobs if j["id"] == thread_id), None)
        
        if not job_object:
            raise HTTPException(status_code=404, detail="Invalid thread ID")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Jobs file not found")
    
    try:
        result_state = run_workflow(user_message, thread_id, job_object)
        # Return the entire state as JSON
        return JSONResponse(content=result_state)
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload_cvs")
async def upload_cvs(
    files: List[UploadFile] = File(...),
    thread_id: str = Form(...)
):
    """Upload CVs endpoint (returns JSON)"""
    print(f"📤 Uploading {len(files)} CVs for thread {thread_id}")
    cvs_dir = f"assets/cvs/{thread_id}"
    os.makedirs(cvs_dir, exist_ok=True)
    success = []
    failed = []
    vector_index = get_vector_index()
    for file in files:
        try:
            content = await file.read()
            file_path = os.path.join(cvs_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            status, filename = process_and_vectorize_cv(
                content,
                file.filename,
                vector_index,
                thread_id
            )
            if status == "success":
                success.append(filename)
            else:
                failed.append(filename)
        except Exception as e:
            print(f"Error uploading {file.filename}: {e}")
            failed.append(file.filename)
    return JSONResponse(content={
        "success": success,
        "failed": failed,
        "total": len(files)
    })


@app.post("/api/initial_filter")
async def initial_filter_endpoint(
    thread_id: str = Form(...),
    filter_config: str = Form(...)
):
    """Apply initial keyword filter (returns JSON)"""
    try:
        config = json.loads(filter_config)
    except:
        raise HTTPException(status_code=400, detail="Invalid filter configuration")
    vector_index = get_vector_index()
    result = apply_initial_filter(thread_id, config, vector_index)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return JSONResponse(content=result)

# --- New Endpoints ---

@app.get("/api/screening_table/{thread_id}")
async def get_screening_table(thread_id: str):
    """Return all screened candidates for a thread, ranked by score desc"""
    query = "SELECT * FROM candidates WHERE thread_id = ? ORDER BY CAST(score AS REAL) DESC"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (thread_id,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    candidates = [dict(zip(columns, row)) for row in rows]
    # Parse JSON fields
    for c in candidates:
        for key in ['universities', 'soft_skills', 'technical_skills', 'Certifications', 'Languages']:
            if key in c and c[key]:
                try:
                    c[key] = json.loads(c[key])
                except:
                    pass
    return JSONResponse(content={"candidates": candidates})

@app.get("/api/jobs")
async def get_jobs():
    """Return all jobs from jobs.json"""
    jobs_path = os.path.join("data", "jobs.json")
    with open(jobs_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    return JSONResponse(content={"jobs": jobs})

class JobCreateRequest(BaseModel):
    title: str = Field(...)
    description: str = Field(...)
    details: str = Field(...)
    location: str = Field(...)
    level: str = Field(...)
    requirements: list = Field(...)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

@app.post("/api/jobs")
async def create_job(job: JobCreateRequest = Body(...)):
    """Create a new job and add it to jobs.json"""
    jobs_path = os.path.join("data", "jobs.json")
    # Load existing jobs
    try:
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except Exception:
        jobs = []
    # Check for duplicate title
    for j in jobs:
        if j["title"].strip().lower() == job.title.strip().lower():
            raise HTTPException(status_code=400, detail="Job title already exists")
    # Generate id from title
    job_id = slugify(job.title)
    # Ensure id is unique
    existing_ids = {j["id"] for j in jobs}
    orig_id = job_id
    i = 2
    while job_id in existing_ids:
        job_id = f"{orig_id}_{i}"
        i += 1
    # Create job dict
    job_dict = {
        "id": job_id,
        "title": job.title,
        "description": job.description,
        "details": job.details,
        "location": job.location,
        "level": job.level,
        "requirements": job.requirements
    }
    jobs.append(job_dict)
    # Write back to file
    with open(jobs_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    return {"success": True, "id": job_id}

@app.get("/api/job_stats")
async def get_job_stats():
    """Return jobs, number of candidates screened, and candidates applied (uploaded)"""
    jobs_path = os.path.join("data", "jobs.json")
    with open(jobs_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    stats = []
    for job in jobs:
        thread_id = job["id"]
        # Candidates screened (in DB)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM candidates WHERE thread_id = ?", (thread_id,))
        screened = cursor.fetchone()[0]
        # Candidates applied (uploaded CVs)
        cvs_dir = f"assets/cvs/{thread_id}"
        applied = 0
        if os.path.exists(cvs_dir):
            applied = len([f for f in os.listdir(cvs_dir) if f.endswith('.pdf')])
        conn.close()
        stats.append({
            "job_id": thread_id,
            "title": job["title"],
            "screened": screened,
            "applied": applied
        })
    return JSONResponse(content={"job_stats": stats})

@app.get("/api/conversation/{thread_id}")
async def get_conversation(thread_id: str):
    """Return conversation history for a thread"""
    conv_store = ConversationStore(thread_id)
    return JSONResponse(content={
        "summary": conv_store.summary,
        "messages": conv_store.recent_messages
    })

@app.get("/api/candidate/{candidate_id}")
async def get_candidate(candidate_id: int):
    """Return candidate details by candidate_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
    row = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate = dict(zip(columns, row))
    for key in ['universities', 'soft_skills', 'technical_skills', 'Certifications', 'Languages']:
        if key in candidate and candidate[key]:
            try:
                candidate[key] = json.loads(candidate[key])
            except:
                pass
    return JSONResponse(content=candidate)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)