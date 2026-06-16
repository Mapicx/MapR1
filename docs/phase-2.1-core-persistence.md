# Phase 2.1: Core Persistence
**Timeline:** Current Implementation  
**Status:** In Progress

---

## Overview

Phase 2.1 focuses on the essential persistence layer - saving scenarios and basic world management. This is the foundation for all future features.

---

## Goals

- ✅ Database connection to Supabase
- ✅ Save generated scenarios to database
- ✅ Basic world/project management
- ✅ Retrieve saved scenarios
- ✅ SQLAlchemy ORM with Alembic migrations

---

## What We're Building

### 1. Database Setup

**Dependencies:**
```toml
sqlalchemy>=2.0.30
alembic>=1.13.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
```

**Database Schema (Phase 2.1):**

```sql
-- Projects/Worlds table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scenarios table
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    request_id UUID,
    prompt TEXT NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    probability FLOAT,
    model_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    saved BOOLEAN DEFAULT FALSE
);

-- Timeline events table
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    description TEXT NOT NULL,
    impact VARCHAR(50) NOT NULL,
    sequence_order INTEGER NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_scenarios_project ON scenarios(project_id);
CREATE INDEX idx_scenarios_created ON scenarios(created_at DESC);
CREATE INDEX idx_timeline_scenario ON timeline_events(scenario_id);
CREATE INDEX idx_timeline_year ON timeline_events(year);
```

---

### 2. SQLAlchemy Models

**Files to Create:**
- `backend/models/db_models.py` - Database models
- `backend/core/database.py` - Database connection

**Models:**

```python
class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID]
    name: Mapped[str]
    description: Mapped[Optional[str]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    
    # Relationships
    scenarios: Mapped[List["DBScenario"]]

class DBScenario(Base):
    __tablename__ = "scenarios"
    
    id: Mapped[uuid.UUID]
    project_id: Mapped[Optional[uuid.UUID]]
    request_id: Mapped[Optional[uuid.UUID]]
    prompt: Mapped[str]
    title: Mapped[str]
    description: Mapped[str]
    category: Mapped[str]
    probability: Mapped[Optional[float]]
    model_used: Mapped[Optional[str]]
    created_at: Mapped[datetime]
    saved: Mapped[bool]
    
    # Relationships
    project: Mapped[Optional["Project"]]
    timeline_events: Mapped[List["DBTimelineEvent"]]

class DBTimelineEvent(Base):
    __tablename__ = "timeline_events"
    
    id: Mapped[uuid.UUID]
    scenario_id: Mapped[uuid.UUID]
    year: Mapped[int]
    description: Mapped[str]
    impact: Mapped[str]
    sequence_order: Mapped[int]
    
    # Relationships
    scenario: Mapped["DBScenario"]
```

---

### 3. Database Connection

**File:** `backend/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

### 4. Alembic Migrations

**Setup:**
```bash
alembic init alembic
```

**Migration Files:**
- `alembic/versions/001_initial_schema.py`

**Commands:**
```bash
# Create migration
alembic revision --autogenerate -m "initial schema"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

### 5. API Routes (Split Files)

**New Structure:**
```
backend/api/
├── __init__.py
├── scenarios.py      # Scenario generation & retrieval
├── projects.py       # Project/world management
└── health.py         # Health checks
```

**Scenario Routes (`scenarios.py`):**
```python
POST   /api/scenarios/generate          # Generate scenarios
GET    /api/scenarios                   # List all scenarios
GET    /api/scenarios/{id}              # Get specific scenario
POST   /api/scenarios/{id}/save         # Save scenario (set saved=true)
DELETE /api/scenarios/{id}              # Delete scenario
GET    /api/scenarios/search            # Search scenarios
```

**Project Routes (`projects.py`):**
```python
POST   /api/projects                    # Create project
GET    /api/projects                    # List projects
GET    /api/projects/{id}               # Get project details
PUT    /api/projects/{id}               # Update project
DELETE /api/projects/{id}               # Delete project
GET    /api/projects/{id}/scenarios     # Get project scenarios
```

---

### 6. Save Flag Implementation

**Scenario Generation Flow:**
1. Generate scenarios (as before)
2. **Automatically save to DB** with `saved=false`
3. Return scenarios with database IDs
4. User can call `POST /api/scenarios/{id}/save` to mark as saved

**Benefits:**
- All generations are logged (analytics)
- Users can review before saving
- Can implement "unsaved scenarios" cleanup later

---

### 7. Updated Scenario Response

**Add database fields:**
```python
class ScenarioResponse(BaseModel):
    request_id: str
    prompt: str
    scenarios: List[Scenario]
    generated_at: datetime
    model_used: str
    saved_to_db: bool = True  # NEW
    db_ids: List[str] = []    # NEW - scenario IDs in database
```

---

## Implementation Steps

### Step 1: Database Setup (Day 1)
1. ✅ Add database dependencies
2. ✅ Create SQLAlchemy models
3. ✅ Set up database connection
4. ✅ Initialize Alembic
5. ✅ Create initial migration
6. ✅ Apply migration to Supabase

### Step 2: Repository Layer (Day 1)
1. ✅ Create `backend/repositories/scenario_repository.py`
2. ✅ Create `backend/repositories/project_repository.py`
3. ✅ Implement CRUD operations
4. ✅ Add transaction handling

### Step 3: API Routes (Day 2)
1. ✅ Split routes into separate files
2. ✅ Update scenario generation to save to DB
3. ✅ Add project management endpoints
4. ✅ Add scenario retrieval endpoints
5. ✅ Add save flag endpoint

### Step 4: Integration (Day 2)
1. ✅ Update main.py to include new routes
2. ✅ Test database connections
3. ✅ Test scenario generation + save
4. ✅ Test project management
5. ✅ Update documentation

---

## Testing Checklist

- [ ] Database connection works
- [ ] Migrations apply successfully
- [ ] Scenarios save to database
- [ ] Scenarios retrieve from database
- [ ] Projects CRUD operations work
- [ ] Save flag toggles correctly
- [ ] Foreign key relationships work
- [ ] Cascade deletes work properly

---

## Success Criteria

Phase 2.1 is complete when:

1. **Persistence Works:**
   - Generate scenario → saved to DB automatically
   - Restart server → scenarios still exist
   
2. **Projects Work:**
   - Create project → scenarios can be associated
   - Delete project → scenarios cascade delete
   
3. **Retrieval Works:**
   - List all scenarios
   - Get specific scenario by ID
   - Filter scenarios by project

**Example Flow:**
```python
# Generate and auto-save
response = POST /api/scenarios/generate
# Returns: scenarios with db_ids

# Mark as saved
POST /api/scenarios/{id}/save

# Retrieve later
scenarios = GET /api/scenarios
```

---

## Files to Create/Modify

### New Files:
- `backend/models/db_models.py`
- `backend/core/database.py`
- `backend/repositories/scenario_repository.py`
- `backend/repositories/project_repository.py`
- `backend/api/scenarios.py`
- `backend/api/projects.py`
- `backend/api/health.py`
- `alembic/versions/001_initial_schema.py`
- `alembic.ini`
- `alembic/env.py`

### Modified Files:
- `main.py` - Include new route modules
- `backend/api/routes.py` - Remove (split into separate files)
- `backend/core/config.py` - Already updated
- `.env` - Add database credentials
- `pyproject.toml` - Already has dependencies

---

## What's NOT in Phase 2.1

❌ Entity system (nations, people, companies)  
❌ Timeline branching  
❌ Memory system (ChromaDB)  
❌ Relationships between entities  
❌ World state tracking  
❌ Event system  

**These will be in Phase 2.2!**

---

## Next: Phase 2.2

After Phase 2.1 is complete, Phase 2.2 will add:
- Entity system
- Timeline branching
- Memory system
- Relationships
- Full world state management

See `phase-2.2-advanced-persistence.md` for details.

---

**Status:** Ready to implement  
**Estimated Time:** 2 days  
**Dependencies:** Supabase credentials (✅ provided)
