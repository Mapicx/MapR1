# Phase 3.1: Agents & Memory Foundation
**Timeline:** Week 5 (Days 1-3)  
**Status:** Not Started  
**Prerequisites:** Phase 2 Complete

---

## Overview

Build the foundation for autonomous agents with memory. This phase creates the basic agent architecture, links agents to entities, and implements agent memory so they can remember past events and form continuity.

**Key Focus:** Agent memory is the foundation for everything else. Without memory, agents can't learn, hold grudges, build trust, or develop culture.

---

## Goals

- ✅ Agent architecture (base class + types)
- ✅ Agent-Entity linking system
- ✅ Agent memory (short-term + long-term)
- ✅ Memory recall and context building
- ✅ Agent persistence in database

---

## What We're Building

### 1. Agent Database Models

**File:** `backend/models/agent_models.py`

```python
class Agent(Base):
    """Autonomous agent that makes decisions"""
    __tablename__ = "agents"
    
    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey("projects.id"))
    entity_id = Column(UUID, ForeignKey("entities.id"), nullable=True)  # Link to entity
    
    # Identity
    name = Column(String(255))
    agent_type = Column(String(50))  # personal, ceo, policy, finance, etc.
    role = Column(String(255))  # "CEO of TechCorp", "President of Nation X"
    
    # State
    personality = Column(JSONB)  # Personality traits
    current_state = Column(JSONB)  # Current emotional/mental state
    resources = Column(JSONB)  # Available resources
    
    # Metadata
    created_at = Column(DateTime)
    last_active = Column(DateTime)
    
    # Relationships
    entity = relationship("Entity", back_populates="agents")
    memories = relationship("AgentMemory", back_populates="agent")


class AgentMemory(Base):
    """Agent's memory of events"""
    __tablename__ = "agent_memories"
    
    id = Column(UUID, primary_key=True)
    agent_id = Column(UUID, ForeignKey("agents.id"))
    
    # Memory content
    memory_type = Column(String(50))  # observation, interaction, decision, emotion
    content = Column(Text)
    importance = Column(Float)  # 0-1 (how important is this memory)
    emotional_valence = Column(Float)  # -1 to 1 (negative to positive)
    
    # Context
    related_agent_ids = Column(ARRAY(UUID))  # Other agents involved
    related_entity_ids = Column(ARRAY(UUID))  # Entities involved
    world_state_snapshot = Column(JSONB)  # World state at time of memory
    
    # Metadata
    occurred_at = Column(DateTime)
    created_at = Column(DateTime)
    
    # Relationships
    agent = relationship("Agent", back_populates="memories")
```

**Why this design:**
- Agent can exist without entity (pure AI agent)
- Entity can have multiple agents (CEO, CFO, etc.)
- Memories stored in both DB (structured) and ChromaDB (semantic)

---

### 2. Agent Types

**File:** `backend/agents/agent_types.py`

```python
class AgentType(Enum):
    # =========================
    # Personal / Individual
    # =========================
    PERSONAL = "personal"
    LEADER = "leader"
    WORKER = "worker"
    ENTREPRENEUR = "entrepreneur"
    INVENTOR = "inventor"
    RESEARCHER = "researcher"
    TEACHER = "teacher"
    DOCTOR = "doctor"
    LAWYER = "lawyer"
    ENGINEER = "engineer"
    FARMER = "farmer"
    ARTIST = "artist"
    WRITER = "writer"
    JOURNALIST = "journalist"
    INFLUENCER = "influencer"
    
    # =========================
    # Business / Company
    # =========================
    CEO = "ceo"
    CFO = "cfo"
    CTO = "cto"
    COO = "coo"
    HR = "hr"
    FINANCE = "finance"
    MARKETING = "marketing"
    SALES = "sales"
    OPERATIONS = "operations"
    PRODUCT_MANAGER = "product_manager"
    RECRUITER = "recruiter"
    INVESTOR = "investor"
    TRADER = "trader"
    
    # =========================
    # Government / Politics
    # =========================
    POLICY = "policy"
    DIPLOMACY = "diplomacy"
    DEFENSE = "defense"
    ECONOMY = "economy"
    TAXATION = "taxation"
    GOVERNOR = "governor"
    MAYOR = "mayor"
    SENATOR = "senator"
    JUDGE = "judge"
    POLICE = "police"
    INTELLIGENCE = "intelligence"
    
    # =========================
    # Military / Security
    # =========================
    COMMANDER = "commander"
    SOLDIER = "soldier"
    SPY = "spy"
    ASSASSIN = "assassin"
    CYBER_SECURITY = "cyber_security"
    
    # =========================
    # Social / Community
    # =========================
    ACTIVIST = "activist"
    ORGANIZER = "organizer"
    MEDIATOR = "mediator"
    NEGOTIATOR = "negotiator"
    RELIGIOUS_LEADER = "religious_leader"
    COMMUNITY_LEADER = "community_leader"
    
    # =========================
    # Criminal / Underground
    # =========================
    HACKER = "hacker"
    SCAMMER = "scammer"
    SMUGGLER = "smuggler"
    GANG_LEADER = "gang_leader"
    MERCENARY = "mercenary"
    
    # =========================
    # Science / Technology
    # =========================
    AI_AGENT = "ai_agent"
    DATA_SCIENTIST = "data_scientist"
    SCIENTIST = "scientist"
    ROBOTICS = "robotics"
    ARCHITECT = "architect"
    
    # =========================
    # Media / Culture
    # =========================
    MUSICIAN = "musician"
    FILMMAKER = "filmmaker"
    DESIGNER = "designer"
    HISTORIAN = "historian"
    PHILOSOPHER = "philosopher"
    
    # =========================
    # Logistics / Infrastructure
    # =========================
    TRANSPORT = "transport"
    SUPPLY_CHAIN = "supply_chain"
    BUILDER = "builder"
    ENERGY_MANAGER = "energy_manager"
    
    # =========================
    # Healthcare / Emergency
    # =========================
    PARAMEDIC = "paramedic"
    SURGEON = "surgeon"
    FIREFIGHTER = "firefighter"
    DISASTER_RESPONSE = "disaster_response"


class Personality(BaseModel):
    """Agent personality traits"""
    
    # Big Five personality traits
    openness: float = 0.5           # 0-1 (conservative to open)
    conscientiousness: float = 0.5  # 0-1 (spontaneous to organized)
    extraversion: float = 0.5       # 0-1 (introverted to extraverted)
    agreeableness: float = 0.5      # 0-1 (competitive to cooperative)
    neuroticism: float = 0.5        # 0-1 (stable to anxious)
    
    # Additional traits
    risk_tolerance: float = 0.5     # 0-1 (risk-averse to risk-seeking)
    ambition: float = 0.5           # 0-1 (content to ambitious)
    empathy: float = 0.5            # 0-1 (cold to empathetic)
    rationality: float = 0.5        # 0-1 (emotional to rational)
    creativity: float = 0.5         # 0-1 (conventional to creative)
    morality: float = 0.5           # 0-1 (pragmatic to principled)


# Agent type categories for easy filtering
AGENT_CATEGORIES = {
    "personal": [
        "personal", "leader", "worker", "entrepreneur", "inventor",
        "researcher", "teacher", "doctor", "lawyer", "engineer",
        "farmer", "artist", "writer", "journalist", "influencer"
    ],
    "business": [
        "ceo", "cfo", "cto", "coo", "hr", "finance", "marketing",
        "sales", "operations", "product_manager", "recruiter",
        "investor", "trader"
    ],
    "government": [
        "policy", "diplomacy", "defense", "economy", "taxation",
        "governor", "mayor", "senator", "judge", "police", "intelligence"
    ],
    "military": [
        "commander", "soldier", "spy", "assassin", "cyber_security"
    ],
    "social": [
        "activist", "organizer", "mediator", "negotiator",
        "religious_leader", "community_leader"
    ],
    "criminal": [
        "hacker", "scammer", "smuggler", "gang_leader", "mercenary"
    ],
    "science": [
        "ai_agent", "data_scientist", "scientist", "robotics", "architect"
    ],
    "media": [
        "musician", "filmmaker", "designer", "historian", "philosopher"
    ],
    "logistics": [
        "transport", "supply_chain", "builder", "energy_manager"
    ],
    "healthcare": [
        "paramedic", "surgeon", "firefighter", "disaster_response"
    ],
}
```

---

### 3. Example Agent Configurations

**Different agent types have different default personalities:**

```python
# CEO - Ambitious, risk-taking, rational
CEO_PERSONALITY = Personality(
    ambition=0.9,
    risk_tolerance=0.7,
    rationality=0.8,
    empathy=0.5,
    morality=0.6,
)

# Activist - Empathetic, principled, passionate
ACTIVIST_PERSONALITY = Personality(
    ambition=0.7,
    empathy=0.9,
    morality=0.9,
    rationality=0.5,
    risk_tolerance=0.6,
)

# Hacker - Creative, risk-taking, low morality
HACKER_PERSONALITY = Personality(
    creativity=0.9,
    risk_tolerance=0.8,
    rationality=0.7,
    morality=0.3,
    empathy=0.4,
)

# Doctor - Empathetic, conscientious, principled
DOCTOR_PERSONALITY = Personality(
    empathy=0.9,
    conscientiousness=0.9,
    morality=0.8,
    rationality=0.7,
    risk_tolerance=0.3,
)

# Spy - Rational, low empathy, risk-taking
SPY_PERSONALITY = Personality(
    rationality=0.9,
    empathy=0.2,
    risk_tolerance=0.8,
    morality=0.4,
    conscientiousness=0.8,
)

# Artist - Creative, open, emotional
ARTIST_PERSONALITY = Personality(
    creativity=0.9,
    openness=0.9,
    rationality=0.3,
    empathy=0.7,
    risk_tolerance=0.6,
)
```

---

### 3. Agent Memory System

**File:** `backend/agents/agent_memory.py`

```python
class AgentMemoryManager:
    """Manages agent memory storage and recall"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
        self.vector_store = get_vector_store()
    
    async def remember(
        self,
        db: AsyncSession,
        memory_type: str,
        content: str,
        importance: float,
        emotional_valence: float = 0.0,
        related_agents: List[UUID] = None,
        related_entities: List[UUID] = None,
        world_state: dict = None,
    ) -> AgentMemory:
        """
        Store a memory in both database and vector store
        
        Args:
            memory_type: observation, interaction, decision, emotion
            content: What happened
            importance: 0-1 (how significant)
            emotional_valence: -1 to 1 (negative to positive)
        """
        # Store in database
        memory = AgentMemory(
            id=uuid4(),
            agent_id=self.agent_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            emotional_valence=emotional_valence,
            related_agent_ids=related_agents or [],
            related_entity_ids=related_entities or [],
            world_state_snapshot=world_state or {},
            occurred_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(memory)
        await db.commit()
        
        # Store in vector store for semantic search
        self.vector_store.add_memory(
            memory_id=f"agent_memory_{memory.id}",
            content=content,
            metadata={
                "agent_id": str(self.agent_id),
                "memory_type": memory_type,
                "importance": importance,
                "emotional_valence": emotional_valence,
                "timestamp": memory.occurred_at.isoformat(),
            }
        )
        
        return memory
    
    async def recall_recent(
        self,
        db: AsyncSession,
        limit: int = 10,
    ) -> List[AgentMemory]:
        """Get recent memories (short-term memory)"""
        result = await db.execute(
            select(AgentMemory)
            .where(AgentMemory.agent_id == self.agent_id)
            .order_by(AgentMemory.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def recall_important(
        self,
        db: AsyncSession,
        threshold: float = 0.7,
        limit: int = 20,
    ) -> List[AgentMemory]:
        """Get important memories"""
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == self.agent_id,
                AgentMemory.importance >= threshold
            )
            .order_by(AgentMemory.importance.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    def recall_similar(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """Semantic search for similar memories"""
        return self.vector_store.search(
            query=query,
            n_results=top_k,
            filters={"agent_id": str(self.agent_id)}
        )
    
    async def recall_about_agent(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
        limit: int = 10,
    ) -> List[AgentMemory]:
        """Get memories involving another agent"""
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == self.agent_id,
                AgentMemory.related_agent_ids.contains([other_agent_id])
            )
            .order_by(AgentMemory.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def build_context(
        self,
        db: AsyncSession,
        situation: str,
    ) -> str:
        """
        Build context for decision-making
        
        Combines:
        - Recent memories (what just happened)
        - Important memories (key events)
        - Relevant memories (similar situations)
        """
        # Get recent memories
        recent = await self.recall_recent(db, limit=5)
        
        # Get important memories
        important = await self.recall_important(db, threshold=0.8, limit=5)
        
        # Get semantically similar memories
        similar = self.recall_similar(situation, top_k=5)
        
        # Build context string
        context_parts = []
        
        if recent:
            context_parts.append("Recent events:")
            for m in recent:
                context_parts.append(f"- {m.content}")
        
        if important:
            context_parts.append("\nImportant memories:")
            for m in important:
                context_parts.append(f"- {m.content}")
        
        if similar:
            context_parts.append("\nSimilar past situations:")
            for m in similar:
                context_parts.append(f"- {m['content']}")
        
        return "\n".join(context_parts)
```

---

### 4. Agent Repository

**File:** `backend/repositories/agent_repository.py`

```python
class AgentRepository:
    """Data access for agents"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_agent(
        self,
        project_id: UUID,
        name: str,
        agent_type: str,
        role: str,
        personality: dict,
        entity_id: Optional[UUID] = None,
    ) -> Agent:
        """Create a new agent"""
        agent = Agent(
            id=uuid4(),
            project_id=project_id,
            entity_id=entity_id,
            name=name,
            agent_type=agent_type,
            role=role,
            personality=personality,
            current_state={},
            resources={},
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
        )
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent
    
    async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID"""
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()
    
    async def list_agents(
        self,
        project_id: Optional[UUID] = None,
        entity_id: Optional[UUID] = None,
    ) -> List[Agent]:
        """List agents with filters"""
        query = select(Agent)
        
        if project_id:
            query = query.where(Agent.project_id == project_id)
        if entity_id:
            query = query.where(Agent.entity_id == entity_id)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_agent_state(
        self,
        agent_id: UUID,
        state_updates: dict,
    ) -> Optional[Agent]:
        """Update agent's current state"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return None
        
        agent.current_state.update(state_updates)
        agent.last_active = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(agent)
        return agent
```

---

### 5. API Endpoints

**File:** `backend/api/agents.py`

```python
# Agent Management
POST   /api/projects/{id}/agents          # Create agent
GET    /api/projects/{id}/agents          # List agents
GET    /api/agents/{id}                   # Get agent
PUT    /api/agents/{id}                   # Update agent
DELETE /api/agents/{id}                   # Delete agent

# Agent Memory
POST   /api/agents/{id}/memories          # Add memory
GET    /api/agents/{id}/memories          # Get memories
GET    /api/agents/{id}/memories/recent   # Recent memories
GET    /api/agents/{id}/memories/important # Important memories
POST   /api/agents/{id}/memories/recall   # Semantic recall
```

---

## Implementation Checklist

### Day 1: Database & Models
- [ ] Create agent_models.py
- [ ] Add Agent table
- [ ] Add AgentMemory table
- [ ] Update Entity model (add agents relationship)
- [ ] Run migrations

### Day 2: Memory System
- [ ] Create agent_memory.py
- [ ] Implement AgentMemoryManager
- [ ] Add remember() method
- [ ] Add recall methods (recent, important, similar)
- [ ] Add build_context() method
- [ ] Test memory storage and recall

### Day 3: Repository & API
- [ ] Create agent_repository.py
- [ ] Implement CRUD operations
- [ ] Create agents.py API
- [ ] Add agent endpoints
- [ ] Add memory endpoints
- [ ] Test API

---

## Success Criteria

Phase 3.1 is complete when:

1. **Agents Exist:**
   - Can create agents
   - Can link agents to entities
   - Agents persist in database

2. **Memory Works:**
   - Agents can store memories
   - Can recall recent memories
   - Can recall important memories
   - Can search memories semantically

3. **Context Building:**
   - Can build decision context from memories
   - Memories include emotional valence
   - Memories track relationships

---

## Example Usage

```python
# Create entity
company = create_entity(project_id, {
    "type": "company",
    "name": "TechCorp"
})

# Create CEO agent for company
ceo = create_agent(project_id, {
    "name": "Sarah Chen",
    "agent_type": "ceo",
    "role": "CEO of TechCorp",
    "entity_id": company.id,
    "personality": {
        "ambition": 0.9,
        "risk_tolerance": 0.7,
        "empathy": 0.6
    }
})

# Agent experiences event
memory_manager = AgentMemoryManager(ceo.id)
await memory_manager.remember(
    db,
    memory_type="interaction",
    content="Competitor launched aggressive pricing strategy",
    importance=0.8,
    emotional_valence=-0.3,  # Negative event
)

# Later, recall context for decision
context = await memory_manager.build_context(
    db,
    situation="Should we lower prices?"
)
# Returns: Recent events + important memories + similar situations
```

---

## Next: Phase 3.2

Once agents have memory, we add:
- Goal system
- Relationship dynamics
- Basic decision-making

Memory is the foundation for everything else!
