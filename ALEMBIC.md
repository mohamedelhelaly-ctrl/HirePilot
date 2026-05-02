# Step 1: Installation
```bash 
$ alembic init alembic
```

# Step 2: Configuration
- update **alembic.ini** with database url
- import SQLAlchemyBase in alembic/env.py
- update target_metada to SQLAlchemyBase.metadata

# Step 3: Migration
```bash
$ alembic revision --autogenerate -m "Init commit"
```

# Step 4: Upgrade Database
```bash
$ alembic upgrade head
```