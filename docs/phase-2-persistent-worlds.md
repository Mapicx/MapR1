# Phase 2: Persistent Worlds
**Timeline:** Week 3-4  
**Status:** Not Started  
**Prerequisites:** Phase 1 Complete

---

## Overview

Transform the system from a stateless scenario generator into a persistent simulation engine. This phase adds memory, world state tracking, and the ability to maintain consistent universes across sessions.

**Key Concept:** Without persistent state, there is no real simulation. This phase is the HEART of the system.

---

## Goals

- ✅ Worlds persist across sessions
- ✅ Entities maintain consistent state
- ✅ Memory system tracks history
- ✅ Branching logic creates alternate timelines
- ✅ Database stores all simulation data

---

## What We're Building

### 1. Database Layer

**Files to Create:**
- `backend/core/database.py` - Database connection
- `database/migrations/001_initial_schema.sql`
- `backend/models/db_models.py` - SQLAlchemy models

**Database Choice:** PostgreSQL (recommended)

**Schema Design:**

```sql
-- Worlds table
CREATE TABLE worlds (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP,
    last_updated TIMESTAMP,
    state JSONB
);

-- Entities table
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    world_id UUID REFERENCES worlds(id),
    type VARCHAR(50),  -- nation, person, company, faction
    name VARCHAR(255),
    attributes JSONB,
    created_at TIMESTAMP
);

-- Events table
CREATE TABLE events (
    id UUID PRIMARY KEY,
    world_id UUID REFERENCES worlds(id),
    timestamp TIMESTAMP,
    description TEXT,
    impact_score FLOAT,
    affected_entities UUID[]
);

-- Timelines table (for branching)
CREATE TABLE timelines (
    id UUID PRIMARY KEY,
    world_id UUID REFERENCES worlds(id),
    parent_timeline_id UUID,
    branch_point TIMESTAMP,
    name VARCHAR(255)
);

-- Relationships table
CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    world_id UUID REFERENCES worlds(id),
    entity_a_id UUID REFERENCES entities(id),
    entity_b_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(50),  -- alliance, enemy, trade, etc.
    strength FLOAT
);
```

---

### 2. World State Engine

**Files to Create:**
- `backend/world_state/world_manager.py`
- `backend/world_state/entity_manager.py`
- `backend/world_state/state_tracker.py`

**Core Responsibilities:**

**World Manager:**
```python
class WorldManager:
    def create_world(self, name: str, initial_state: dict) -> World:
        """Create a new persistent world"""
        pass
    
    def get_world(self, world_id: str) -> World:
        """Retrieve world state"""
        pass
    
    def update_world(self, world_id: str, changes: dict) -> World:
        """Apply changes to world state"""
        pass
    
    def list_worlds(self) -> List[World]:
        """Get all worlds"""
        pass
```

**Entity Manager:**
```python
class EntityManager:
    def create_entity(self, world_id: str, entity_data: dict) -> Entity:
        """Add entity to world"""
        pass
    
    def update_entity(self, entity_id: str, changes: dict) -> Entity:
        """Modify entity state"""
        pass
    
    def get_entities(self, world_id: str, filters: dict = None) -> List[Entity]:
        """Query entities"""
        pass
```

**State Tracker:**
```python
class StateTracker:
    def record_event(self, world_id: str, event: Event) -> None:
        """Log world event"""
        pass
    
    def get_history(self, world_id: str, start: datetime, end: datetime) -> List[Event]:
        """Retrieve historical events"""
        pass
    
    def get_current_state(self, world_id: str) -> dict:
        """Get complete world snapshot"""
        pass
```

---

### 3. Entity System

**Files to Create:**
- `backend/models/entity.py`
- `backend/world_state/entity_types.py`

**Entity Types:**

```python
class Entity(BaseModel):
    id: str
    world_id: str
    type: EntityType
    name: str
    attributes: dict
    
class Nation(Entity):
    economy: float  # 0-100
    stability: float
    military_power: float
    population: int
    alliances: List[str]
    
class Person(Entity):
    role: str
    influence: float
    goals: List[str]
    
class Company(Entity):
    industry: str
    market_cap: float
    employees: int
    
class Faction(Entity):
    ideology: str
    members: int
    resources: dict
```

**Example Entity Data:**
```json
{
  "id": "nation_001",
  "type": "nation",
  "name": "Neo Tokyo",
  "attributes": {
    "economy": 74,
    "stability": 55,
    "military_power": 68,
    "population": 45000000,
    "alliances": ["Europa", "Pacific Union"],
    "resources": {
      "energy": 85,
      "food": 60,
      "technology": 92
    }
  }
}
```

---

### 4. Memory System

**Files to Create:**
- `backend/memory/vector_store.py`
- `backend/memory/memory_manager.py`
- `backend/memory/embeddings.py`

**Purpose:**
- Store simulation history
- Enable semantic search over past events
- Track patterns and recurring themes
- Provide context for future simulations

**Implementation:**

**Vector Database:** ChromaDB (recommended for Phase 2)

```python
class MemoryManager:
    def __init__(self):
        self.vector_store = ChromaDB()
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    def store_memory(self, world_id: str, content: str, metadata: dict):
        """Store event/state in vector DB"""
        embedding = self.embedder.encode(content)
        self.vector_store.add(
            embedding=embedding,
            metadata={
                "world_id": world_id,
                "timestamp": datetime.now(),
                **metadata
            }
        )
    
    def recall_similar(self, query: str, world_id: str, top_k: int = 5):
        """Find similar past events"""
        query_embedding = self.embedder.encode(query)
        return self.vector_store.query(
            embedding=query_embedding,
            filter={"world_id": world_id},
            n_results=top_k
        )
    
    def get_world_history(self, world_id: str) -> List[dict]:
        """Retrieve all memories for a world"""
        pass
```

---

### 5. Branching Engine

**Files to Create:**
- `backend/simulation/branching_engine.py`
- `backend/models/timeline.py`

**Purpose:**
Create alternate reality branches from decision points.

**Core Logic:**

```python
class BranchingEngine:
    def create_branch(
        self, 
        world_id: str, 
        branch_point: datetime,
        decision: str
    ) -> Timeline:
        """
        Create alternate timeline from decision point
        
        Example:
        - Original: "Nation A declares war"
        - Branch: "Nation A pursues diplomacy"
        """
        # 1. Copy world state at branch point
        # 2. Create new timeline record
        # 3. Apply alternate decision
        # 4. Return new timeline ID
        pass
    
    def get_branches(self, world_id: str) -> List[Timeline]:
        """Get all timeline branches for a world"""
        pass
    
    def compare_timelines(self, timeline_a: str, timeline_b: str) -> dict:
        """Compare outcomes between branches"""
        pass
```

**Data Structure:**
```python
class Timeline(BaseModel):
    id: str
    world_id: str
    parent_timeline_id: Optional[str]
    branch_point: datetime
    name: str
    description: str
    divergence_events: List[Event]
```

**Example:**
```
Main Timeline
    ↓
2035: AGI Discovered
    ↓
    ├─→ Branch A: Open Source AGI
    │   └─→ Rapid democratization
    │
    └─→ Branch B: Corporate Control
        └─→ Monopolization
```

---

## API Endpoints to Add

```python
# World Management
POST   /api/worlds                    # Create new world
GET    /api/worlds                    # List all worlds
GET    /api/worlds/{id}               # Get world details
PUT    /api/worlds/{id}               # Update world state
DELETE /api/worlds/{id}               # Delete world

# Entities
POST   /api/worlds/{id}/entities      # Add entity
GET    /api/worlds/{id}/entities      # List entities
PUT    /api/entities/{id}             # Update entity
DELETE /api/entities/{id}             # Remove entity

# Events
POST   /api/worlds/{id}/events        # Record event
GET    /api/worlds/{id}/events        # Get event history

# Timelines
POST   /api/worlds/{id}/branch        # Create timeline branch
GET    /api/worlds/{id}/timelines     # List all branches
GET    /api/timelines/{id}            # Get timeline details

# Memory
GET    /api/worlds/{id}/memory        # Query world memories
POST   /api/worlds/{id}/memory/search # Semantic search
```

---

## Implementation Steps

### Week 3

**Day 1-2: Database Setup**
1. Install PostgreSQL
2. Create database schema
3. Set up SQLAlchemy models
4. Create migration scripts
5. Test database connections

**Day 3-4: World State Engine**
1. Implement WorldManager
2. Implement EntityManager
3. Implement StateTracker
4. Create CRUD operations
5. Test persistence

**Day 5: Entity System**
1. Define entity types
2. Create entity models
3. Implement entity creation/updates
4. Test entity relationships

### Week 4

**Day 1-2: Memory System**
1. Install ChromaDB
2. Set up embeddings
3. Implement MemoryManager
4. Test memory storage/retrieval
5. Integrate with world state

**Day 3-4: Branching Engine**
1. Design branching logic
2. Implement timeline creation
3. Add branch comparison
4. Test alternate realities

**Day 5: Integration & Testing**
1. Connect all components
2. Test end-to-end flows
3. Fix bugs
4. Performance optimization

---

## Technical Requirements

### New Dependencies

```toml
[project]
dependencies = [
    # Existing from Phase 1...
    
    # Database
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "alembic>=1.12.0",
    
    # Vector DB & Embeddings
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
    
    # Utilities
    "uuid>=1.30",
    "python-dateutil>=2.8.0",
]
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/aethermind
DATABASE_POOL_SIZE=10

# Vector DB
CHROMA_PERSIST_DIR=./embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Memory
MEMORY_RETENTION_DAYS=365
MAX_MEMORIES_PER_QUERY=10
```

---

## Testing Checklist

- [ ] Database schema created successfully
- [ ] Worlds persist across server restarts
- [ ] Entities maintain consistent state
- [ ] Events are recorded chronologically
- [ ] Memory system stores and retrieves data
- [ ] Embeddings are generated correctly
- [ ] Branching creates independent timelines
- [ ] Timeline comparison works
- [ ] All API endpoints respond correctly
- [ ] No data loss on updates

---

## Success Criteria

**Phase 2 is complete when:**

1. **Persistence Works:**
   - Create a world, restart server, world still exists
   
2. **Entities Evolve:**
   - Create entities, update them, changes persist
   
3. **Memory Functions:**
   - Store events, query similar events, get relevant results
   
4. **Branching Works:**
   - Create branch from timeline, both evolve independently

**Example Working Flow:**
```python
# Session 1
world = create_world("Cyberpunk 2077")
add_entity(world.id, Nation("Neo Tokyo"))
record_event(world.id, "Mega-corp war begins")

# Server restart

# Session 2
world = get_world(world.id)  # Still exists!
history = get_history(world.id)  # Events preserved!
branch = create_branch(world.id, "Peace treaty signed")
```

---

## Known Limitations (To Address in Later Phases)

- ❌ No autonomous agent behavior
- ❌ No automatic world evolution
- ❌ No conflict/cooperation logic
- ❌ No visualization
- ❌ No UI for world exploration

---

## Next Phase Preview

**Phase 3** will add:
- Autonomous agents with goals
- Agent decision-making
- Conflict and cooperation
- Emergent behavior
- Relationship dynamics

This will bring the worlds to life with intelligent actors.

---

## Notes

- **Database is critical** - invest time in good schema design
- **Test persistence early** - don't assume it works
- **Memory system is powerful** - enables context-aware simulations
- **Branching is complex** - start simple, iterate
- **Performance matters** - index database properly

**Key Insight:** This phase transforms the system from a toy into a real simulation engine. Take time to get it right.
