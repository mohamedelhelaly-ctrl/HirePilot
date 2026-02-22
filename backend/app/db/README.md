# Incorta-HR Backend - Database Layer

This directory contains all database-related code for the Incorta-HR system.

## Structure

```
db/
├── __init__.py          # Package initialization
├── database.py          # Database connection and session management
├── models.py            # SQLAlchemy ORM models (11 tables)
└── crud.py              # CRUD operations for all models
```

## Database Tables

1. **users** - HR Managers and Hiring Managers with roles
2. **requisitions** - Job openings synced from Lever with batch processing counters
3. **candidates** - Immutable personal profiles (reused across applications)
4. **applications** - Links candidates to requisitions; holds all mutable state
5. **application_details** - Normalized CV fields for fast filtering
6. **screening_results** - Detailed AI screening breakdowns
7. **interview_sessions** - Scheduled and completed interviews
8. **transcript_chunks** - Real-time transcript pieces from live interviews
9. **status_history** - Immutable audit trail of status changes
10. **webhook_events** - Log of all incoming Lever webhooks
11. **refresh_tokens** - Active JWT refresh tokens

## Key Design Principles

- **Async-first**: All database operations use `asyncpg` and `AsyncSession`
- **Immutable audit trail**: Status history is append-only
- **Idempotency**: Webhook events are deduplicated by `lever_event_id`
- **Batch processing**: Counter-based thresholds trigger automated re-screening
- **Relationships**: SQLAlchemy relationships enable efficient eager loading

## Usage

### Database Connection

```python
from app.db.database import get_db

async def some_endpoint(db: AsyncSession = Depends(get_db)):
    # Use db session
    pass
```

### CRUD Operations

```python
from app.db import crud
from app.db.database import get_db

# Create a candidate
candidate = await crud.create_candidate(db, candidate_data)

# Get applications by requisition, ordered by score
apps = await crud.get_applications_by_requisition(
    db, 
    requisition_id=1, 
    min_score=7.0,
    include_relations=True
)

# Update application status with audit trail
await crud.update_application_status(
    db,
    application_id=123,
    new_status=ApplicationStatus.ASSESSMENT_SENT,
    user_id=1,
    reason="Passed initial screening"
)
```

## Migrations

Database migrations are managed with Alembic:

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

## Environment Variables

Required database configuration (see `.env.example`):

```
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=incorta_hr
```
