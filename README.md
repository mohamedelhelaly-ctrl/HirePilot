# HirePilot

HirePilot is an AI-assisted recruiting platform for internal HR teams. The repository contains a FastAPI backend, a React/Vite frontend, and supporting documentation for the HirePilot prototype described in the thesis notes.

## What this repository contains

- A backend service built with FastAPI, SQLAlchemy, Alembic, and Pydantic.
- A LangGraph-based orchestration layer for screening, interview support, and related AI workflows.
- A React + Vite frontend for authentication, requisition views, candidate workflows, and interview-related experiences.
- Documentation that connects the implementation to the thesis narrative and product specification.

## Current implementation highlights

### Backend
- Authentication and authorization with JWT and Google OAuth support.
- Requisition CRUD and assignment management.
- Candidate and application endpoints, including immutable candidate-directory views and application status updates.
- Interview support with WebSocket-based live transcription and follow-up question generation.
- Chat endpoints for threaded, requisition-scoped conversations.
- Google Calendar / Meet integration and background scheduler support.

### Frontend
- React + Vite application under the frontend workspace.
- Google sign-in via OAuth and API integration for the backend.
- UI structure for requisitions, candidates, and interview-oriented flows.

## Repository layout

```text
HirePilot/
├── alembic/                  # Database migrations
├── mds/                      # Thesis source and planning notes
├── src/
│   ├── backend/              # FastAPI application, routers, models, graphs
│   └── frontend/             # React/Vite frontend
├── requirements.txt          # Python dependencies
├── project_spec.md           # Product and architecture summary
├── SETUP_COMPLETE.md         # Local setup guide
└── README.md                 # Repository overview
```

## Quick start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Node.js 20+

### 2. Create a Python environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the backend working directory before launching the service. A minimal example is:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=incorta_hr
DB_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/incorta_hr
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
ENCRYPTION_KEY=replace-me-with-a-strong-secret
SCREENING_POLL_INTERVAL_MINUTES=15
NEW_CANDIDATE_THRESHOLD=10
NEW_ASSESSMENT_THRESHOLD=5
```

### 4. Prepare the database
```bash
alembic upgrade head
```

### 5. Start the backend
```bash
cd src/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- http://localhost:8000/
- http://localhost:8000/health
- http://localhost:8000/docs

### 6. Start the frontend
```bash
cd <frontend-app-directory>
npm install
npm run dev
```

## Main API areas

- Authentication: `/api/auth`
- Requisitions: `/api/requisitions`
- Candidates and applications: `/api/candidates`
- Interviews: `/api/interview`
- Chat: `/api/chat`
- Calendar: `/api/calendar`

## Documentation

- [project_spec.md](project_spec.md) — product scope, architecture, and implementation notes
- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) — local setup and development workflow
- [mds/HirePilot_Thesis.md](mds/HirePilot_Thesis.md) — thesis source document for the project

## Notes for contributors

- The implementation is evolving, so documentation should be kept in sync with the code.
- Some AI workflows depend on external credentials and model downloads at runtime.
- The thesis document remains the best source for the broader product narrative and system goals.
