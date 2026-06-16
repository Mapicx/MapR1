# Phase 3.2: Goals & Relationship Dynamics
**Timeline:** Week 5 (Days 4-5) + Week 6 (Days 1-2)  
**Status:** Not Started  
**Prerequisites:** Phase 3.1 Complete

---

## Overview

Add goal-driven behavior and dynamic relationships. Agents now have motivations (goals) and form evolving relationships with other agents. This creates the foundation for emergent social dynamics.

**Key Focus:** Goals drive action. Relationships create complexity. Together they produce emergence.

---

## Goals

- ✅ Goal system (creation, tracking, prioritization)
- ✅ Relationship dynamics (formation, evolution, decay)
- ✅ Relationship memory (agents remember interactions)
- ✅ Trust and influence tracking
- ✅ Social network formation

---

## What We're Building

### 1. Goal Database Models

**File:** `backend/models/goal_models.py`

```python
class Goal(Base):
    """Agent goal/motivation"""
    __tablename__ = "goals"
    
    id = Column(UUID, primary_key=True)
    agent_id = Column(UUID, ForeignKey("agents.id"))
    parent_goal_id = Column(UUID, ForeignKey("goals.id"), nullable=True)  # Sub-goals
    
    # Goal definition
    description = Column(Text)
    goal_type = Column(String(50))  # survival, power, wealth, knowledge, etc.
    priority = Column(Float)  # 0-1
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0-1
    status = Column(String(50))  # active, completed, abandoned, blocked
    
    # Timeline
    created_at = Column(DateTime)
    deadline = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="goals")
    sub_goals = relationship("Goal", backref="parent_goal", remote_side=[id])


class GoalType(Enum):
    # Basic needs
    SURVIVAL = "survival"
    SECURITY = "security"
    
    # Power & influence
    POWER = "power"
    INFLUENCE = "influence"
    DOMINANCE = "dominance"
    
    # Resources
    WEALTH = "wealth"
    RESOURCES = "resources"
    
    # Knowledge & growth
    KNOWLEDGE = "knowledge"
    INNOVATION = "innovation"
    
    # Social
    RELATIONSHIPS = "relationships"
    REPUTATION = "reputation"
    REVENGE = "revenge"
    
    # Ideological
    IDEOLOGY = "ideology"
    JUSTICE = "justice"
    FREEDOM = "freedom"
```

---

### 2. Relationship Database Models

**File:** `backend/models/relationship_models.py`

```python
class AgentRelationship(Base):
    """Relationship between two agents"""
    __tablename__ = "agent_relationships"
    
    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey("projects.id"))
    
    # Agents involved
    agent_a_id = Column(UUID, ForeignKey("agents.id"))
    agent_b_id = Column(UUID, ForeignKey("agents.id"))
    
    # Relationship properties
    relationship_type = Column(String(50))  # ally, enemy, neutral, mentor, etc.
    strength = Column(Float)  # -1 to 1 (hostile to friendly)
    trust = Column(Float)  # 0 to 1
    influence = Column(Float)  # -1 to 1 (who influences whom)
    
    # History
    interaction_count = Column(Integer, default=0)
    last_interaction = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationships
    agent_a = relationship("Agent", foreign_keys=[agent_a_id])
    agent_b = relationship("Agent", foreign_keys=[agent_b_id])
    interactions = relationship("AgentInteraction", back_populates="relationship")


class AgentInteraction(Base):
    """Record of interaction between agents"""
    __tablename__ = "agent_interactions"
    
    id = Column(UUID, primary_key=True)
    relationship_id = Column(UUID, ForeignKey("agent_relationships.id"))
    
    # Interaction details
    interaction_type = Column(String(50))  # cooperation, conflict, trade, communication
    description = Column(Text)
    outcome = Column(String(50))  # positive, negative, neutral
    
    # Impact on relationship
    trust_change = Column(Float)  # How much trust changed
    strength_change = Column(Float)  # How much strength changed
    
    # Metadata
    occurred_at = Column(DateTime)
    
    # Relationships
    relationship = relationship("AgentRelationship", back_populates="interactions")


class RelationshipType(Enum):
    # Positive
    ALLY = "ally"
    FRIEND = "friend"
    MENTOR = "mentor"
    PARTNER = "partner"
    
    # Negative
    ENEMY = "enemy"
    RIVAL = "rival"
    
    # Neutral
    NEUTRAL = "neutral"
    ACQUAINTANCE = "acquaintance"
    
    # Hierarchical
    SUPERIOR = "superior"
    SUBORDINATE = "subordinate"
    
    # Economic
    TRADE_PARTNER = "trade_partner"
    COMPETITOR = "competitor"
```

---

### 3. Goal System

**File:** `backend/agents/goal_system.py`

```python
class GoalManager:
    """Manages agent goals"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
    
    async def add_goal(
        self,
        db: AsyncSession,
        description: str,
        goal_type: str,
        priority: float,
        deadline: Optional[datetime] = None,
        parent_goal_id: Optional[UUID] = None,
    ) -> Goal:
        """Add a new goal"""
        goal = Goal(
            id=uuid4(),
            agent_id=self.agent_id,
            parent_goal_id=parent_goal_id,
            description=description,
            goal_type=goal_type,
            priority=priority,
            progress=0.0,
            status="active",
            created_at=datetime.utcnow(),
            deadline=deadline,
        )
        db.add(goal)
        await db.commit()
        return goal
    
    async def get_active_goals(
        self,
        db: AsyncSession,
    ) -> List[Goal]:
        """Get all active goals, sorted by priority"""
        result = await db.execute(
            select(Goal)
            .where(
                Goal.agent_id == self.agent_id,
                Goal.status == "active"
            )
            .order_by(Goal.priority.desc())
        )
        return list(result.scalars().all())
    
    async def update_progress(
        self,
        db: AsyncSession,
        goal_id: UUID,
        progress: float,
    ) -> Goal:
        """Update goal progress"""
        result = await db.execute(
            select(Goal).where(Goal.id == goal_id)
        )
        goal = result.scalar_one_or_none()
        
        if goal:
            goal.progress = min(1.0, max(0.0, progress))
            
            # Mark as completed if progress = 1.0
            if goal.progress >= 1.0:
                goal.status = "completed"
                goal.completed_at = datetime.utcnow()
            
            await db.commit()
        
        return goal
    
    async def reprioritize(
        self,
        db: AsyncSession,
        situation: str,
    ) -> List[Goal]:
        """
        Adjust goal priorities based on current situation
        
        Example:
        - If under attack, survival goals become priority
        - If wealthy, expansion goals increase
        """
        goals = await self.get_active_goals(db)
        
        # Simple heuristic-based reprioritization
        # (In Phase 3.3, we'll use LLM for this)
        
        for goal in goals:
            # Survival goals always high priority in danger
            if "danger" in situation.lower() and goal.goal_type == "survival":
                goal.priority = min(1.0, goal.priority + 0.2)
            
            # Wealth goals lower priority in crisis
            elif "crisis" in situation.lower() and goal.goal_type == "wealth":
                goal.priority = max(0.0, goal.priority - 0.1)
        
        await db.commit()
        return goals
    
    async def get_goal_context(
        self,
        db: AsyncSession,
    ) -> str:
        """Build context string of current goals"""
        goals = await self.get_active_goals(db)
        
        if not goals:
            return "No active goals."
        
        context_parts = ["Current goals:"]
        for goal in goals[:5]:  # Top 5 goals
            context_parts.append(
                f"- {goal.description} "
                f"(priority: {goal.priority:.1f}, progress: {goal.progress:.0%})"
            )
        
        return "\n".join(context_parts)
```

---

### 4. Relationship System

**File:** `backend/agents/relationship_system.py`

```python
class RelationshipManager:
    """Manages agent relationships"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
    
    async def get_relationship(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
    ) -> Optional[AgentRelationship]:
        """Get relationship with another agent"""
        result = await db.execute(
            select(AgentRelationship).where(
                or_(
                    and_(
                        AgentRelationship.agent_a_id == self.agent_id,
                        AgentRelationship.agent_b_id == other_agent_id
                    ),
                    and_(
                        AgentRelationship.agent_a_id == other_agent_id,
                        AgentRelationship.agent_b_id == self.agent_id
                    )
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_relationship(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
        relationship_type: str,
        strength: float = 0.0,
        trust: float = 0.5,
    ) -> AgentRelationship:
        """Create or update relationship"""
        existing = await self.get_relationship(db, other_agent_id)
        
        if existing:
            # Update existing
            existing.relationship_type = relationship_type
            existing.strength = strength
            existing.trust = trust
            existing.updated_at = datetime.utcnow()
            await db.commit()
            return existing
        else:
            # Create new
            relationship = AgentRelationship(
                id=uuid4(),
                project_id=None,  # Will be set from agent
                agent_a_id=self.agent_id,
                agent_b_id=other_agent_id,
                relationship_type=relationship_type,
                strength=strength,
                trust=trust,
                influence=0.0,
                interaction_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(relationship)
            await db.commit()
            return relationship
    
    async def record_interaction(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
        interaction_type: str,
        description: str,
        outcome: str,
        trust_change: float = 0.0,
        strength_change: float = 0.0,
    ) -> AgentInteraction:
        """Record an interaction between agents"""
        # Get or create relationship
        relationship = await self.get_relationship(db, other_agent_id)
        if not relationship:
            relationship = await self.create_or_update_relationship(
                db, other_agent_id, "neutral"
            )
        
        # Create interaction record
        interaction = AgentInteraction(
            id=uuid4(),
            relationship_id=relationship.id,
            interaction_type=interaction_type,
            description=description,
            outcome=outcome,
            trust_change=trust_change,
            strength_change=strength_change,
            occurred_at=datetime.utcnow(),
        )
        db.add(interaction)
        
        # Update relationship
        relationship.trust = max(0.0, min(1.0, relationship.trust + trust_change))
        relationship.strength = max(-1.0, min(1.0, relationship.strength + strength_change))
        relationship.interaction_count += 1
        relationship.last_interaction = datetime.utcnow()
        relationship.updated_at = datetime.utcnow()
        
        # Update relationship type based on strength
        if relationship.strength > 0.7:
            relationship.relationship_type = "ally"
        elif relationship.strength < -0.7:
            relationship.relationship_type = "enemy"
        elif abs(relationship.strength) < 0.3:
            relationship.relationship_type = "neutral"
        
        await db.commit()
        return interaction
    
    async def get_all_relationships(
        self,
        db: AsyncSession,
    ) -> List[AgentRelationship]:
        """Get all relationships for this agent"""
        result = await db.execute(
            select(AgentRelationship).where(
                or_(
                    AgentRelationship.agent_a_id == self.agent_id,
                    AgentRelationship.agent_b_id == self.agent_id
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_allies(
        self,
        db: AsyncSession,
    ) -> List[UUID]:
        """Get IDs of allied agents"""
        relationships = await self.get_all_relationships(db)
        allies = []
        
        for rel in relationships:
            if rel.relationship_type == "ally" or rel.strength > 0.5:
                # Get the other agent's ID
                other_id = rel.agent_b_id if rel.agent_a_id == self.agent_id else rel.agent_a_id
                allies.append(other_id)
        
        return allies
    
    async def get_enemies(
        self,
        db: AsyncSession,
    ) -> List[UUID]:
        """Get IDs of enemy agents"""
        relationships = await self.get_all_relationships(db)
        enemies = []
        
        for rel in relationships:
            if rel.relationship_type == "enemy" or rel.strength < -0.5:
                other_id = rel.agent_b_id if rel.agent_a_id == self.agent_id else rel.agent_a_id
                enemies.append(other_id)
        
        return enemies
    
    async def get_relationship_context(
        self,
        db: AsyncSession,
    ) -> str:
        """Build context string of relationships"""
        relationships = await self.get_all_relationships(db)
        
        if not relationships:
            return "No relationships."
        
        context_parts = ["Relationships:"]
        for rel in relationships[:10]:  # Top 10
            other_id = rel.agent_b_id if rel.agent_a_id == self.agent_id else rel.agent_a_id
            context_parts.append(
                f"- Agent {other_id}: {rel.relationship_type} "
                f"(strength: {rel.strength:.1f}, trust: {rel.trust:.1f})"
            )
        
        return "\n".join(context_parts)
```

---

## API Endpoints

```python
# Goals
POST   /api/agents/{id}/goals              # Add goal
GET    /api/agents/{id}/goals              # Get goals
PUT    /api/goals/{id}                     # Update goal
DELETE /api/goals/{id}                     # Delete goal
POST   /api/goals/{id}/progress            # Update progress

# Relationships
GET    /api/agents/{id}/relationships      # Get relationships
POST   /api/agents/{id}/relationships      # Create relationship
PUT    /api/relationships/{id}             # Update relationship
POST   /api/relationships/{id}/interact    # Record interaction
GET    /api/agents/{id}/allies             # Get allies
GET    /api/agents/{id}/enemies            # Get enemies
```

---

## Implementation Checklist

### Day 4: Goal System
- [ ] Create goal_models.py
- [ ] Add Goal table
- [ ] Create goal_system.py
- [ ] Implement GoalManager
- [ ] Add goal API endpoints
- [ ] Test goal creation and tracking

### Day 5 + Day 1: Relationship System
- [ ] Create relationship_models.py
- [ ] Add AgentRelationship table
- [ ] Add AgentInteraction table
- [ ] Create relationship_system.py
- [ ] Implement RelationshipManager
- [ ] Add relationship API endpoints

### Day 2: Integration
- [ ] Test goal-driven behavior
- [ ] Test relationship formation
- [ ] Test interaction recording
- [ ] Test relationship evolution

---

## Success Criteria

Phase 3.2 is complete when:

1. **Goals Work:**
   - Agents can have multiple goals
   - Goals have priorities
   - Progress can be tracked

2. **Relationships Form:**
   - Agents can form relationships
   - Relationships have types and strength
   - Trust can increase/decrease

3. **Interactions Matter:**
   - Interactions affect relationships
   - Positive interactions build trust
   - Negative interactions damage relationships

---

## Example Usage

```python
# Agent has goals
goal_manager = GoalManager(ceo.id)
await goal_manager.add_goal(
    db,
    description="Increase market share to 30%",
    goal_type="wealth",
    priority=0.9
)

# Agents interact
rel_manager = RelationshipManager(ceo.id)
await rel_manager.record_interaction(
    db,
    other_agent_id=competitor_ceo.id,
    interaction_type="conflict",
    description="Price war initiated",
    outcome="negative",
    trust_change=-0.2,
    strength_change=-0.3
)

# Relationship becomes hostile
relationship = await rel_manager.get_relationship(db, competitor_ceo.id)
# relationship.type = "rival", strength = -0.3
```

---

## Next: Phase 3.3

Once agents have goals and relationships, we add:
- LLM-powered decision-making
- Emergent behavior
- Automatic simulation

Goals + Relationships + Memory = Foundation for emergence!
