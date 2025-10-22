import os
import uuid
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
from pydantic import BaseModel

from config.database_config import initialize_database
from config.vector_config import get_vector_index
from utils.cv_processing import process_and_vectorize_cv
from utils.initial_filter import apply_initial_filter
from graph import run_workflow
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

# Job descriptions for demo
JOB_DESCRIPTIONS = {
    "senior_ai_ml": """Senior AI/ML Engineer
Cairo / COGS - Professional Services / Full-time

Incorta is a next-generation data analytics and business intelligence platform that excels at rapidly delivering business value from transactional data. We provide an integrated end-to-end data experience, from data acquisition and enrichment to visualizing and sharing results.

As a Senior GenAI Developer at Incorta, you'll lead the creation of cutting-edge generative AI solutions leveraging Retrieval-Augmented Generation (RAG) and Large Language Models (LLMs). You will play a key role in developing agentic solutions that empower our customers by enhancing decision-making processes and optimizing their analytics workflows.

YOU WILL:
- Data Analysis & Modeling: Collect, clean, and analyze large datasets to identify trends, patterns, and insights.
- Machine Learning & AI: Develop and deploy predictive models, recommendation systems, and AI-driven solutions.
- Architected, developed, and deployed GenAI solutions integrated with RAG and LLM frameworks.
- Design and engineer sophisticated prompts and fine-tune LLMs to achieve optimal performance.
- Business Impact: Work closely with product, marketing, and engineering teams to provide data-driven solutions.
- Data Visualization: Communicate findings effectively using dashboards and visual tools.
- Optimization & Automation: Enhance existing models and automate data workflows for efficiency.
- Collaboration: Partner with data engineers and business stakeholders to improve data quality and strategy.

YOU HAVE:
- Bachelor's or Master's degree in Computer Science, Data Science, Statistics, or a related field.
- 5+ years of experience in data science, machine learning, or a related field.
- Strong programming skills in Python, R, or SQL.
- Experience with machine learning frameworks such as TensorFlow, Scikit-learn, or PyTorch.
- Proven ability to build and deploy AI/ML solutions at scale.
- Strong communication skills and ability to clearly articulate complex technical concepts.

Additional Requirements:
- This position requires up to 90% travel throughout the year, both domestically and potentially internationally.
- Flexibility in schedule and location is essential.
- Must be comfortable working in dynamic environments and adapting quickly to changing business needs.""",
    
    "junior_ai": """Junior AI Engineer
Cairo / COGS - Professional Services / Full-time

Incorta is a next-generation data analytics and business intelligence platform that excels at rapidly delivering business value from transactional data. We're looking for passionate individuals eager to start their career in artificial intelligence.

As a Junior AI Engineer at Incorta, you'll work alongside senior engineers to build and deploy AI solutions that drive real impact. This is an excellent opportunity to learn and grow in a fast-paced, innovative environment.

YOU WILL:
- Support the design, training, and optimization of ML and deep learning models.
- Prepare and transform datasets for AI/ML pipelines.
- Run experiments, analyze results, and improve model performance.
- Collaborate with senior engineers and cross-functional teams to bring AI solutions into production.
- Stay curious and keep up with the latest AI tools and frameworks.
- Assist in data analysis and visualization tasks.
- Document technical processes and findings.

YOU HAVE:
- Bachelor's degree in Computer Science, AI, Data Science, or related field (Master's a plus).
- 0-2 years of experience in AI/ML or related field.
- Knowledge of machine learning, deep learning, and statistical modeling.
- Hands-on experience with Python and ML libraries (TensorFlow, PyTorch, Scikit-learn).
- Exposure to cloud platforms (AWS, Azure, GCP) is a bonus.
- Strong problem-solving, analytical, and teamwork skills.
- Eagerness to learn and adapt to new technologies.

WHAT WE OFFER:
- Competitive salary & performance-based bonuses.
- Health and life insurance coverage.
- Learning opportunities, certifications, and clear career growth paths.
- A collaborative, innovative culture where your ideas matter.
- Mentorship from experienced AI professionals.

Location: Cairo (Hybrid options available)
Reporting to: AI Lead / Senior AI Engineer

At Incorta, we believe in empowering people to innovate, grow, and make a sustainable impact. We welcome applicants from all backgrounds and are proud to be an equal opportunity employer."""
}

# Request model
class ChatRequest(BaseModel):
    user_message: str
    thread_id: str

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main UI with job threads"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Incorta Recruitment System</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 50px;
            }
            .header img {
                height: 60px;
                background: white;
                padding: 10px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .header h1 {
                font-size: 48px;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }
            .header p {
                font-size: 20px;
                opacity: 0.9;
            }
            .jobs-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 30px;
                margin-top: 40px;
            }
            .job-card {
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                cursor: pointer;
            }
            .job-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0,0,0,0.3);
            }
            .job-title {
                font-size: 28px;
                color: #667eea;
                margin-bottom: 10px;
                font-weight: 600;
            }
            .job-meta {
                color: #666;
                margin-bottom: 20px;
                font-size: 14px;
            }
            .job-description {
                color: #444;
                line-height: 1.6;
                margin-bottom: 20px;
            }
            .job-requirements {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .job-requirements h4 {
                color: #667eea;
                margin-bottom: 10px;
                font-size: 16px;
            }
            .job-requirements ul {
                list-style: none;
                padding-left: 0;
            }
            .job-requirements li {
                padding: 5px 0;
                color: #555;
            }
            .job-requirements li:before {
                content: "✓ ";
                color: #667eea;
                font-weight: bold;
                margin-right: 8px;
            }
            .apply-btn {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: 600;
                transition: opacity 0.3s ease;
            }
            .apply-btn:hover {
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="/assets/logo.png" alt="Incorta Logo">
                <h1>🚀 Incorta Careers</h1>
                <p>Join our innovative team and shape the future of data analytics</p>
            </div>
            
            <div class="jobs-grid">
                <div class="job-card" onclick="window.location.href='/chat?thread_id=senior_ai_ml'">
                    <div class="job-title">Senior AI/ML Engineer</div>
                    <div class="job-meta">📍 Cairo, Egypt • 💼 Full-time • 💰 Competitive</div>
                    <div class="job-description">
                        Lead the creation of cutting-edge generative AI solutions leveraging RAG and LLMs. 
                        Develop agentic solutions that empower customers by enhancing decision-making processes.
                    </div>
                    <div class="job-requirements">
                        <h4>Key Requirements:</h4>
                        <ul>
                            <li>5+ years in AI/ML development</li>
                            <li>Python, TensorFlow, PyTorch</li>
                            <li>Experience with RAG and LLM frameworks</li>
                            <li>Strong communication skills</li>
                        </ul>
                    </div>
                    <a href="/chat?thread_id=senior_ai_ml" class="apply-btn">View Position →</a>
                </div>
                
                <div class="job-card" onclick="window.location.href='/chat?thread_id=junior_ai'">
                    <div class="job-title">Junior AI Engineer</div>
                    <div class="job-meta">📍 Cairo, Egypt • 💼 Full-time • 🎓 Entry Level</div>
                    <div class="job-description">
                        Start your career in AI! Work alongside senior engineers to build and deploy AI solutions. 
                        Perfect opportunity to learn and grow in a fast-paced, innovative environment.
                    </div>
                    <div class="job-requirements">
                        <h4>Key Requirements:</h4>
                        <ul>
                            <li>0-2 years experience in AI/ML</li>
                            <li>Bachelor's in Computer Science or related</li>
                            <li>Python and ML libraries (TensorFlow, Scikit-learn)</li>
                            <li>Eagerness to learn and grow</li>
                        </ul>
                    </div>
                    <a href="/chat?thread_id=junior_ai" class="apply-btn">View Position →</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(thread_id: str):
    """Chat interface for specific job thread with upload/filter capabilities"""

    job_title = "Senior AI/ML Engineer" if thread_id == "senior_ai_ml" else "Junior AI Engineer"

    # Load conversation history
    conv_store = ConversationStore(thread_id)
    messages_html = ""
    for msg in conv_store.recent_messages:
        role = "You" if msg["role"] == "user" else "Assistant"
        messages_html += f"""
        <div class="message {'user-message' if msg['role'] == 'user' else 'assistant-message'}">
            <strong>{role}:</strong><br>
            {msg['content']}
        </div>
        """

    # If no messages, add the welcome message
    if not messages_html:
        messages_html = f"""
        <div class="message assistant-message">
            <strong>Assistant:</strong><br>
            Hello! I'm your recruitment assistant for the {job_title} position. How can I help you today?
            <br><br>
            💡 <strong>Quick tips:</strong>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li>Use the upload button to upload candidate resumes</li>
                <li>Use the filter button above for initial keyword screening</li>
                <li>Ask me to "screen the CVs" after uploading</li>
                <li>Query candidates: "show me candidates with Python experience"</li>
                <li>Get insights: "why did candidate X score higher than Y?"</li>
            </ul>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{job_title} - Incorta Recruitment</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                flex: 1;
                display: flex;
                flex-direction: column;
            }}
            .header {{
                background: #1a2332;
                color: white;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            .logo {{
                height: 40px;
                background: white;
                padding: 5px;
                border-radius: 5px;
            }}
            .header-title {{
                text-align: center;
                flex: 1;
            }}
            .header-title h1 {{
                font-size: 24px;
                margin-bottom: 5px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            }}
            .header-title p {{
                font-size: 14px;
                opacity: 0.9;
            }}
            .back-btn {{
                background: rgba(255,255,255,0.1);
                padding: 8px 16px;
                border-radius: 20px;
                text-decoration: none;
                color: white;
                font-size: 14px;
                font-weight: 600;
                transition: background 0.3s ease;
            }}
            .back-btn:hover {{
                background: rgba(255,255,255,0.2);
            }}
            .filter-toggle {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 20px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                text-align: center;
                margin-bottom: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                transition: opacity 0.3s ease;
            }}
            .filter-toggle:hover {{
                opacity: 0.9;
            }}
            .filter-dropdown {{
                display: none;
                background: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                margin-bottom: 20px;
            }}
            .filter-dropdown.active {{
                display: block;
            }}
            .filter-section {{
                margin-bottom: 15px;
            }}
            .filter-section label {{
                display: block;
                margin-bottom: 5px;
                font-size: 14px;
                color: #444;
                font-weight: 600;
            }}
            .filter-section input {{
                width: 100%;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #ddd;
                font-size: 14px;
                outline: none;
            }}
            .filter-section input:focus {{
                border-color: #667eea;
            }}
            .filter-section button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                width: 100%;
                transition: opacity 0.3s ease;
            }}
            .filter-section button:hover {{
                opacity: 0.9;
            }}
            .chat-container {{
                flex: 1;
                display: flex;
                flex-direction: column;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                padding: 20px;
            }}
            .messages {{
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .message {{
                margin-bottom: 15px;
                padding: 15px;
                border-radius: 10px;
                line-height: 1.6;
            }}
            .user-message {{
                background: #e3f2fd;
                margin-left: 20%;
            }}
            .assistant-message {{
                background: #f5f5f5;
                margin-right: 20%;
            }}
            .input-container {{
                display: flex;
                gap: 10px;
                padding: 15px;
            }}
            .input-container input {{
                flex: 1;
                padding: 12px 20px;
                border: 2px solid #e0e0e0;
                border-radius: 25px;
                font-size: 16px;
                outline: none;
            }}
            .input-container input:focus {{
                border-color: #667eea;
            }}
            .input-container button {{
                padding: 12px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                cursor: pointer;
                font-weight: 600;
                transition: opacity 0.3s ease;
            }}
            .input-container button:hover {{
                opacity: 0.9;
            }}
            .upload-btn {{
                background: #2c3e50;
                color: white;
            }}
            .upload-btn:hover {{
                background: #1a2332;
            }}
            .loading {{
                display: none;
                text-align: center;
                padding: 10px;
                color: #667eea;
                font-weight: 600;
            }}
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }}
            .modal-content {{
                background: white;
                margin: 5% auto;
                padding: 30px;
                border-radius: 15px;
                width: 90%;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            .modal-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .modal-header h2 {{
                color: #667eea;
                font-size: 20px;
            }}
            .close {{
                color: #aaa;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }}
            .close:hover {{
                color: #000;
            }}
            .file-upload {{
                border: 2px dashed #667eea;
                border-radius: 10px;
                padding: 30px;
                text-align: center;
                margin: 20px 0;
            }}
            .file-upload input[type="file"] {{
                margin: 10px 0;
            }}
            .modal-btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                width: 100%;
                transition: opacity 0.3s ease;
            }}
            .modal-btn:hover {{
                opacity: 0.9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-btn">← Back to Jobs</a>
                <div class="header-title">
                    <h1>{job_title}</h1>
                    <p>Thread ID: {thread_id}</p>
                </div>
                <img src="/assets/logo.png" alt="Incorta Logo" class="logo">
            </div>
            <button class="clear-chat-btn" onclick="clearChat()">Clear Chat</button>
            <div class="filter-toggle" onclick="toggleFilter()">🔍 Filter Candidates</div>
            <div class="filter-dropdown" id="filterDropdown">
                <div class="filter-section">
                    <label for="techSkills">Technical Skills (comma-separated):</label>
                    <input type="text" id="techSkills" placeholder="e.g. Python, TensorFlow, PyTorch">
                </div>
                <div class="filter-section">
                    <label for="languages">Languages (comma-separated):</label>
                    <input type="text" id="languages" placeholder="e.g. English, Arabic, French">
                </div>
                <div class="filter-section">
                    <label for="certificates">Certificates (comma-separated):</label>
                    <input type="text" id="certificates" placeholder="e.g. AWS, PMP, Scrum">
                </div>
                <div class="filter-section">
                    <label for="education">Education Degree (comma-separated):</label>
                    <input type="text" id="education" placeholder="e.g. Bachelor, Master, PhD">
                </div>
                <button onclick="applyFilter()">Apply Filter</button>
            </div>
            <div class="chat-container">
                <div class="messages" id="messages">
                    {messages_html}
                </div>
                <div class="loading" id="loading">
                    ⏳ Processing your request...
                </div>
                <div class="input-container">
                    <input type="text" id="messageInput" placeholder="Ask me anything about this position..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">Send</button>
                    <button class="upload-btn" onclick="openUploadModal()">📤 Upload CVs</button>
                </div>
            </div>
            <!-- Upload Modal -->
            <div id="uploadModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>📤 Upload CVs</h2>
                        <span class="close" onclick="closeUploadModal()">&times;</span>
                    </div>
                    <div class="file-upload">
                        <p>Select PDF files to upload</p>
                        <input type="file" id="cvFiles" multiple accept=".pdf">
                        <p style="margin-top: 10px; font-size: 14px; color: #666;">
                            You can select multiple PDF files
                        </p>
                    </div>
                    <button class="modal-btn" onclick="uploadCVs()">Upload</button>
                </div>
            </div>
        </div>
        <script>
            const threadId = "{thread_id}";
            function toggleFilter() {{
                const filterDropdown = document.getElementById('filterDropdown');
                filterDropdown.classList.toggle('active');
            }}
            function handleKeyPress(event) {{
                if (event.key === 'Enter') {{
                    sendMessage();
                }}
            }}
            async function sendMessage() {{
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                if (!message) return;
                addMessage('user', message);
                input.value = '';
                document.getElementById('loading').style.display = 'block';
                try {{
                    const response = await fetch('/api/chat', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            user_message: message,
                            thread_id: threadId
                        }})
                    }});
                    const data = await response.text();
                    addMessage('assistant', data);
                }} catch (error) {{
                    addMessage('assistant', '❌ Error: ' + error.message);
                }} finally {{
                    document.getElementById('loading').style.display = 'none';
                }}
            }}
            function addMessage(role, content) {{
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{role}}-message`;
                messageDiv.innerHTML = `<strong>${{role === 'user' ? 'You' : 'Assistant'}}:</strong><br>${{content}}`;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}
            function openUploadModal() {{
                document.getElementById('uploadModal').style.display = 'block';
            }}
            function closeUploadModal() {{
                document.getElementById('uploadModal').style.display = 'none';
            }}
            async function uploadCVs() {{
                const files = document.getElementById('cvFiles').files;
                if (files.length === 0) {{
                    alert('Please select at least one PDF file');
                    return;
                }}
                const formData = new FormData();
                formData.append('thread_id', threadId);
                for (let file of files) {{
                    formData.append('files', file);
                }}
                addMessage('user', `Uploading ${{files.length}} CV(s)...`);
                closeUploadModal();
                document.getElementById('loading').style.display = 'block';
                try {{
                    const response = await fetch('/api/upload_cvs', {{
                        method: 'POST',
                        body: formData
                    }});
                    const result = await response.json();
                    let message = `✅ Upload complete!<br>Success: ${{result.success.length}}<br>Failed: ${{result.failed.length}}`;
                    if (result.success.length > 0) {{
                        message += `<br><br>Uploaded files:<ul>${{result.success.map(f => '<li>' + f + '</li>').join('')}}</ul>`;
                    }}
                    addMessage('assistant', message);
                }} catch (error) {{
                    addMessage('assistant', '❌ Upload failed: ' + error.message);
                }} finally {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('cvFiles').value = '';
                }}
            }}
            async function applyFilter() {{
                const techSkills = document.getElementById('techSkills').value.split(',').map(s => s.trim()).filter(s => s);
                const languages = document.getElementById('languages').value.split(',').map(s => s.trim()).filter(s => s);
                const certificates = document.getElementById('certificates').value.split(',').map(s => s.trim()).filter(s => s);
                const education = document.getElementById('education').value.split(',').map(s => s.trim()).filter(s => s);
                const config = {{
                    "Technical Skills": {{
                        "keywords": techSkills,
                        "required_ratio": 0.6
                    }},
                    "Languages": {{
                        "keywords": languages,
                        "required_ratio": 0.3
                    }},
                    "Certificates": {{
                        "keywords": certificates,
                        "required_ratio": 0.3
                    }},
                    "Education Degree": {{
                        "keywords": education,
                        "required_ratio": 0.3
                    }}
                }};
                addMessage('user', 'Applying keyword filter...');
                document.getElementById('loading').style.display = 'block';
                try {{
                    const formData = new FormData();
                    formData.append('thread_id', threadId);
                    formData.append('filter_config', JSON.stringify(config));
                    const response = await fetch('/api/initial_filter', {{
                        method: 'POST',
                        body: formData
                    }});
                    const result = await response.text();
                    addMessage('assistant', result);
                }} catch (error) {{
                    addMessage('assistant', '❌ Filter failed: ' + error.message);
                }} finally {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('filterDropdown').classList.remove('active');
                }}
            }}
            async function clearChat() {{
                if (confirm("Are you sure you want to clear the chat history?")) {{
                    try {{
                        const response = await fetch('/api/clear_chat', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                thread_id: threadId
                            }})
                        }});
                        if (response.ok) {{
                            window.location.reload();
                        }}
                    }} catch (error) {{
                        addMessage('assistant', '❌ Error clearing chat: ' + error.message);
                    }}
                }}
            }}
            window.onclick = function(event) {{
                if (event.target.className === 'modal') {{
                    event.target.style.display = 'none';
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint"""
    
    user_message = request.user_message
    thread_id = request.thread_id
    
    if not user_message or not user_message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Get job description for thread
    job_description = JOB_DESCRIPTIONS.get(thread_id)
    
    if not job_description:
        raise HTTPException(status_code=404, detail="Invalid thread ID")
    
    try:
        # Run workflow
        result_state = run_workflow(user_message, thread_id, job_description)
        response_html = result_state.get("response_message", "")
        
        return HTMLResponse(content=response_html)
    
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
    """Upload CVs endpoint"""
    
    print(f"📤 Uploading {len(files)} CVs for thread {thread_id}")
    
    # Create directory for thread
    cvs_dir = f"assets/cvs/{thread_id}"
    os.makedirs(cvs_dir, exist_ok=True)
    
    success = []
    failed = []
    
    # Get vector index
    vector_index = get_vector_index()
    
    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            # Save to disk
            file_path = os.path.join(cvs_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Vectorize
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
    
    return {
        "success": success,
        "failed": failed,
        "total": len(files)
    }

@app.post("/api/initial_filter")
async def initial_filter_endpoint(
    thread_id: str = Form(...),
    filter_config: str = Form(...)
):
    """Apply initial keyword filter"""
    
    try:
        config = json.loads(filter_config)
    except:
        raise HTTPException(status_code=400, detail="Invalid filter configuration")
    
    vector_index = get_vector_index()
    result = apply_initial_filter(thread_id, config, vector_index)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    html_response = f"""
    <div style="padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <h2 style="color: #667eea;">🔍 Initial Filtration Results</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Total CVs:</strong> {result['total']}</p>
            <p style="color: #10b981;"><strong>Passed:</strong> {len(result['passed'])}</p>
            <p style="color: #ef4444;"><strong>Failed:</strong> {len(result['failed'])}</p>
        </div>
        
        <div style="margin-top: 20px;">
            <h3 style="color: #10b981;">✅ Passed CVs:</h3>
            <ul>
                {''.join([f'<li>{cv}</li>' for cv in result['passed']])}
            </ul>
        </div>
        
        <div style="margin-top: 20px;">
            <h3 style="color: #ef4444;">❌ Failed CVs:</h3>
            <ul>
                {''.join([f'<li>{cv}</li>' for cv in result['failed']])}
            </ul>
        </div>
    </div>
    """
    
    return HTMLResponse(content=html_response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)