# Incorta-HR Backend

FastAPI-based backend for the Incorta-HR recruitment assistant.

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp ../.env.example ../.env
```

### 3. Run Database Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head
```

### 4. Start the Server

```bash
# Option 1: Using the run script
chmod +x run.sh
./run.sh

# Option 2: Direct uvicorn command
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health status

### Requisitions
- `POST /api/requisitions/` - Create a new requisition
- `GET /api/requisitions/` - List all requisitions (with filters)
- `GET /api/requisitions/{id}` - Get a specific requisition
- `PATCH /api/requisitions/{id}` - Update a requisition
- `DELETE /api/requisitions/{id}` - Soft delete a requisition

## Creating a Requisition

### Example Request

```bash
curl -X POST http://localhost:8000/api/requisitions/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Backend Engineer",
    "description": "We are looking for an experienced backend engineer...",
    "department": "Engineering",
    "location": "San Francisco, CA",
    "hiring_manager_id": null
  }'
```

### Example Response

```json
{
  "id": 1,
  "lever_id": "lever_a1b2c3d4e5f6g7h8",
  "title": "Senior Backend Engineer",
  "description": "We are looking for an experienced backend engineer...",
  "department": "Engineering",
  "location": "San Francisco, CA",
  "hiring_manager_id": null,
  "is_active": true,
  "new_candidate_counter": 0,
  "new_candidate_threshold": 10,
  "new_assessment_counter": 0,
  "new_assessment_threshold": 5,
  "new_interview_counter": 0,
  "new_interview_threshold": 3,
  "last_screening_at": null,
  "created_at": "2026-02-16T10:30:00Z",
  "updated_at": "2026-02-16T10:30:00Z"
}
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── api/
│   │   └── routers/
│   │       └── requisitions.py  # Requisition endpoints
│   ├── db/
│   │   ├── database.py      # Database connection
│   │   ├── models.py        # SQLAlchemy models
│   │   └── crud.py          # CRUD operations
│   └── schemas/
│       └── __init__.py      # Pydantic schemas
├── alembic/                 # Database migrations
├── requirements.txt
└── run.sh                   # Startup script
```

## Development Notes

- The `lever_id` is auto-generated as a UUID when creating requisitions
- The database ID is auto-incremented by PostgreSQL
- All timestamps are stored in UTC
- The application uses async/await for all database operations
