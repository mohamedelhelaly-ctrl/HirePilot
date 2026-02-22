# Incorta-HR

AI-powered recruitment assistant for Incorta's internal HR team. Automates candidate screening, assessment dispatch, interview scheduling, live interview support, and candidate ranking.

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Incorta-HR
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start PostgreSQL and Redis**
   ```bash
   # Using Docker (recommended)
   docker run -d --name incorta-postgres -p 5432:5432 \
     -e POSTGRES_DB=incorta_hr \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=your_password \
     postgres:14

   docker run -d --name incorta-redis -p 6379:6379 redis:7
   ```

5. **Run database migrations**
   ```bash
   cd backend
   alembic upgrade head
   ```

6. **Start the FastAPI server**
   ```bash
   chmod +x run.sh
   ./run.sh
   # Or: uvicorn app.main:app --reload
   ```

7. **Test the API**
   ```bash
   python test_create_requisition.py
   ```

## API Documentation

Once the server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
incorta-hr/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI initialization
│   │   ├── api/             # REST + WebSocket routers
│   │   │   └── routers/
│   │   │       └── requisitions.py
│   │   ├── db/              # Database layer
│   │   │   ├── database.py  # Connection setup
│   │   │   ├── models.py    # SQLAlchemy models (11 tables)
│   │   │   └── crud.py      # CRUD operations
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # External service clients (TBD)
│   │   ├── graphs/          # LangGraph orchestration (TBD)
│   │   └── utils/           # Utilities (TBD)
│   ├── alembic/             # Database migrations
│   ├── run.sh               # Start script
│   └── test_create_requisition.py
├── frontend/                # React frontend (TBD)
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── project_spec.md          # Full technical specification
```

## Current Features

✅ **Database Layer**
- 11 PostgreSQL tables with full relationships
- Async SQLAlchemy with asyncpg
- Alembic migrations
- Comprehensive CRUD operations

✅ **API - Requisitions**
- Create requisition (auto-generates `lever_id`)
- List requisitions with filters
- Get requisition by ID
- Update requisition
- Soft delete requisition

## Creating Your First Requisition

### Via cURL
```bash
curl -X POST http://localhost:8000/api/requisitions/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Backend Engineer",
    "description": "Looking for an experienced Python developer",
    "department": "Engineering",
    "location": "Remote",
    "hiring_manager_id": null
  }'
```

### Via Python
```python
import httpx
import asyncio

async def create_req():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/requisitions/",
            json={
                "title": "Data Scientist",
                "description": "ML and analytics expert needed",
                "department": "Data",
                "location": "San Francisco"
            }
        )
        print(response.json())

asyncio.run(create_req())
```

## Next Steps

- [ ] Implement authentication (JWT)
- [ ] Add remaining routers (candidates, applications, interviews)
- [ ] Integrate LangGraph orchestration
- [ ] Connect external services (Lever, HackerRank, Google Calendar)
- [ ] Implement WebSocket endpoints
- [ ] Build React frontend

## Documentation

- [Project Specification](project_spec.md) - Complete technical design
- [Database README](backend/app/db/README.md) - Database schema details
- [Backend README](backend/README.md) - API documentation

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI |
| Database | PostgreSQL + asyncpg |
| Vector DB | Chroma (TBD) |
| Cache | Redis (TBD) |
| Orchestration | LangGraph (TBD) |
| LLM | Claude/Gemini (TBD) |
| STT | Whisper (TBD) |
| Frontend | React + TypeScript (TBD) |

---

## Previous Demo System (Legacy)

<details>
<summary>Click to expand old README</summary>

# Incorta Recruitment Demo System

A comprehensive AI-powered recruitment system with CV screening, RAG-based candidate analysis, and intelligent querying capabilities.

## 🚀 Features

- **Multi-threaded Job Management**: Separate recruitment threads for different positions
- **CV Upload & Vectorization**: Automatic CV processing and embedding storage
- **Initial Keyword Filtering**: Pre-screening based on required skills
- **AI-Powered Screening**: Match candidates against job descriptions with scoring
- **RAG Explanations**: Qualitative analysis explaining why candidates scored certain ways
- **Talk to Data**: Natural language queries to filter and analyze candidates
- **Conversation Memory**: Context-aware conversations with summary + recent messages

## 📋 Prerequisites

- Python 3.9+
- Google Gemini API key
- 4GB+ RAM recommended

## 🔧 Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd recruitment_demo
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file:
```
GOOGLE_API_KEY=your_google_gemini_api_key_here
DB_PATH=database/store/candidates.db
TABLE_NAME=candidates
ENCODER_MODEL_DIR=database/store/encoder_model
INDEX_STORE_PATH=database/store/index_store
CVS_PATH=assets/cvs
```

5. **Initialize directories**
```bash
mkdir -p assets/cvs
mkdir -p database/store
mkdir -p database/store/index_store
```

## 🎯 Usage

### Start the application
```bash
python main.py
```

The application will be available at `http://localhost:8000`

### Using the Web Interface

1. **View Jobs**: Navigate to homepage to see available positions
2. **Select Position**: Click on a job card to enter the chat interface
3. **Upload CVs**: Use the upload endpoint or integrate file upload in UI
4. **Screen Candidates**: Ask "screen the CVs" or "screen 20 CVs"
5. **Query Data**: "show candidates with Python" or "list top 10 by score"
6. **Get Insights**: "why did candidate 5 score higher than candidate 3?"

### API Endpoints

#### Chat Endpoint
```bash
POST /api/chat
{
  "user_message": "screen the CVs",
  "thread_id": "senior_ai_ml"
}
```

#### Upload CVs
```bash
POST /api/upload_cvs
Content-Type: multipart/form-data

files: [file1.pdf, file2.pdf, ...]
thread_id: senior_ai_ml
```

#### Initial Filter
```bash
POST /api/initial_filter
Content-Type: application/x-www-form-urlencoded

thread_id: senior_ai_ml
filter_config: {
  "Technical Skills": {
    "keywords": ["Python", "Machine Learning", "TensorFlow"],
    "required_ratio": 0.6
  }
}
```

## 📁 Project Structure
```
recruitment_demo/
├── main.py                 # FastAPI application
├── graph.py               # LangGraph workflow
├── requirements.txt       # Dependencies
├── .env                  # Environment variables
├── config/               # Configuration files
│   ├── llm_config.py
│   ├── vector_config.py
│   └── database_config.py
├── models/               # Data models
│   ├── state.py
│   ├── conversation.py
│   ├── cv_schema.py
│   └── jd_schema.py
├── nodes/                # Workflow nodes
│   ├── routing.py
│   ├── generic.py
│   ├── screening.py
│   ├── rag_explainer.py
│   └── talk_to_data.py
├── utils/                # Utility functions
│   ├── cv_processing.py
│   ├── cv_extraction.py
│   ├── screening_engine.py
│   ├── rag_retrieval.py
│   └── sql_generator.py
├── prompts/              # LLM prompts
│   ├── routing_prompt.py
│   ├── extraction_prompt.py
│   └── rag_prompt.py
├── database/             # Database files
│   ├── schema.py
│   └── store/
└── assets/               # Uploaded CVs
    └── cvs/
```

## 🎨 Workflow
```mermaid
graph TD
    A[User Input] --> B[Routing Node]
    B --> C{Intent?}
    C -->|Generic| D[Generic Node]
    C -->|Screen| E[Screening Node]
    C -->|Explain| F[RAG Explainer Node]
    C -->|Query| G[Talk to Data Node]
    E --> H[Background RAG Indexing]
    D --> I[Response]
    E --> I
    F --> I
    G --> I
```

## 🔑 Key Components

### LangGraph Workflow
- **Routing Node**: Classifies user intent
- **Generic Node**: Handles general questions
- **Screening Node**: Scores CVs against JD
- **RAG Explainer**: Provides qualitative analysis
- **Talk to Data**: SQL-based queries

### Conversation Store
- Maintains summary + last 5 messages per thread
- Auto-summarizes old messages using LLM
- Persistent storage per thread

### Vector Database
- Chroma for CV chunk storage
- Separate RAG index for candidate profiles
- Thread-based isolation

## 🧪 Testing
```python
# Test workflow
from graph import run_workflow

result = run_workflow(
    "screen the CVs",
    thread_id="senior_ai_ml",
    job_description="AI Engineer with 5+ years experience..."
)

print(result["response_message"])
```

## 🐛 Troubleshooting

### Common Issues

1. **"No text extracted from CV"**
   - Ensure PDFs are text-based (not images)
   - Check PDF file is not corrupted

2. **"Vector index not found"**
   - Run initialization: `mkdir -p database/store/index_store`

3. **"Google API error"**
   - Verify API key in `.env`
   - Check API quota limits

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Support

For support, email: support@example.com

## DB update
alembic revision --autogenerate -m "initial schema"
alembic upgrade head 