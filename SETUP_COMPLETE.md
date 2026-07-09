# HirePilot Setup Guide

This document reflects the current repository layout and provides a practical setup path for local development.

## 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 20+
- A working terminal with access to the repository

## 2. Backend environment

Create a `.env` file in the backend working directory before starting the API server. The backend reads environment variables through the configuration layer in [src/backend/helpers/config.py](src/backend/helpers/config.py).

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

## 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Prepare the database

Create a PostgreSQL database named `incorta_hr`, then run:

```bash
alembic upgrade head
```

## 5. Start the backend

```bash
cd src/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Useful endpoints:
- http://localhost:8000/health
- http://localhost:8000/docs

## 6. Start the frontend

```bash
cd <frontend-app-directory>
npm install
npm run dev
```

The Vite app will usually be available at http://localhost:5173.

## 7. Main API areas

| Area | Base path |
|---|---|
| Authentication | `/api/auth` |
| Requisitions | `/api/requisitions` |
| Candidates and applications | `/api/candidates` |
| Interviews | `/api/interview` |
| Chat | `/api/chat` |
| Calendar | `/api/calendar` |

## 8. What is already present

- Authentication and role-aware dependencies
- Requisition CRUD operations
- Candidate and application management endpoints
- Interview and chat routers
- Google Calendar integration services
- LangGraph orchestration modules for AI-driven flows

## 9. Notes

- Full Google OAuth and calendar workflows require valid credentials.
- Some AI-driven modules may download or initialize local models on startup.
- For the broader product story and architecture context, refer to [mds/HirePilot_Thesis.md](mds/HirePilot_Thesis.md).
