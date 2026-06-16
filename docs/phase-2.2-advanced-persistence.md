# Phase 2.2: Advanced Persistence
**Timeline:** After Phase 2.1  
**Status:** Not Started

---

## Overview

Phase 2.2 adds the advanced features from the original Phase 2: entities, timeline branching, memory system, and full world state management.

---

## What Will Be Implemented

### 1. Entity System

**New Tables:**
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    type VARCHAR(50) NOT NULL,  -- nation, person, company, faction
    name VARCHAR(255) NOT NULL,
    attributes JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE entity_types (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    schema JSONB NOT NULL  -- JSON schema for attributes
);
```

**Entity Types:**
- Nations
- People
- Companies
- Factions

---

### 2. Timeline Branching

**New Tables:**
```sql
CREATE TABLE timelines (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    parent_timeline_id UUID REFERENCES timelines(id),
    branch_point TIMESTAMP,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE timeline_scenarios (
    timeline_id UUID REFERENCES timelines(id),
    scenario_id UUID REFERENCES scenarios(id),
    PRIMARY KEY (timeline_id, scenario_id)
);
```

**Features:**
- Create alternate timelines from decision points
- Compare timeline outcomes
- Merge timelines
- Timeline visualization data

---

### 3. Memory System (ChromaDB)

**Implementation:**
- Local ChromaDB instance
- Store scenario embeddings
- Semantic search over past scenarios
- Pattern recognition
- Similar scenario retrieval

**Files:**
- `backend/memory/vector_store.py`
- `backend/memory/memory_manager.py`
- `backend/memory/embeddings.py`

**Features:**
```python
# Store scenario in memory
memory.store(scenario, embedding)

# Find similar scenarios
similar = memory.search("fusion energy future", top_k=5)

# Get world history
history = memory.get_world_history(project_id)
```

---

### 4. Relationships

**New Tables:**
```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    entity_a_id UUID REFERENCES entities(id),
    entity_b_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(50) NOT NULL,
    strength FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Relationship Types:**
- Alliance
- Enemy
- Trade Partner
- Neutral
- Rival

---

### 5. World State Tracking

**New Tables:**
```sql
CREATE TABLE world_states (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    timeline_id UUID REFERENCES timelines(id),
    timestamp TIMESTAMP NOT NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE world_events (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    timeline_id UUID REFERENCES timelines(id),
    event_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    impact_score FLOAT,
    affected_entities UUID[],
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 6. State Snapshots

**Features:**
- Save world state at any point
- Restore to previous state
- Compare states across time
- Track state evolution

---

## API Endpoints (Phase 2.2)

### Entities
```
POST   /api/projects/{id}/entities
GET    /api/projects/{id}/entities
GET    /api/entities/{id}
PUT    /api/entities/{id}
DELETE /api/entities/{id}
```

### Timelines
```
POST   /api/projects/{id}/timelines
GET    /api/projects/{id}/timelines
GET    /api/timelines/{id}
POST   /api/timelines/{id}/branch
GET    /api/timelines/compare
```

### Relationships
```
POST   /api/relationships
GET    /api/projects/{id}/relationships
PUT    /api/relationships/{id}
DELETE /api/relationships/{id}
```

### Memory
```
POST   /api/memory/search
GET    /api/projects/{id}/memory
GET    /api/memory/patterns
```

### World State
```
GET    /api/projects/{id}/state
POST   /api/projects/{id}/state/snapshot
GET    /api/projects/{id}/state/history
POST   /api/projects/{id}/state/restore
```

---

## Implementation Checklist

### Entities
- [ ] Create entity tables
- [ ] Create entity models
- [ ] Implement entity CRUD
- [ ] Add entity type validation
- [ ] Test entity creation

### Timeline Branching
- [ ] Create timeline tables
- [ ] Implement branching logic
- [ ] Add timeline comparison
- [ ] Test branch creation

### Memory System
- [ ] Set up ChromaDB
- [ ] Implement embeddings
- [ ] Create memory manager
- [ ] Add semantic search
- [ ] Test memory retrieval

### Relationships
- [ ] Create relationship tables
- [ ] Implement relationship CRUD
- [ ] Add relationship types
- [ ] Test relationship creation

### World State
- [ ] Create state tables
- [ ] Implement state snapshots
- [ ] Add state restoration
- [ ] Test state tracking

---

## Dependencies

```toml
[project]
dependencies = [
    # Existing...
    
    # Vector DB & Embeddings
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    
    # Graph operations (for relationships)
    "networkx>=3.3",
]
```

---

## Success Criteria

Phase 2.2 is complete when:

1. **Entities Work:**
   - Create entities of different types
   - Associate with projects
   - Query and filter entities

2. **Branching Works:**
   - Create timeline branches
   - Compare outcomes
   - Navigate between timelines

3. **Memory Works:**
   - Store scenario embeddings
   - Search semantically
   - Find similar scenarios

4. **Relationships Work:**
   - Create relationships between entities
   - Query relationship networks
   - Update relationship strength

5. **State Tracking Works:**
   - Save world snapshots
   - Restore previous states
   - Track state evolution

---

## Estimated Timeline

- **Entities:** 1 day
- **Timeline Branching:** 1 day
- **Memory System:** 1 day
- **Relationships:** 0.5 days
- **World State:** 0.5 days
- **Testing & Integration:** 1 day

**Total:** ~5 days

---

## Notes

- Phase 2.2 builds on Phase 2.1 foundation
- All features are independent and can be implemented incrementally
- Memory system can be added last if needed
- Focus on entities and branching first (most important)

---

**Status:** Planned  
**Prerequisites:** Phase 2.1 Complete  
**Estimated Time:** 5 days
