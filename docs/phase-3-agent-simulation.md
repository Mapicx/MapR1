# Phase 3: Agent Simulation
**Timeline:** Week 5-6  
**Status:** Not Started  
**Prerequisites:** Phase 1 & 2 Complete

---

## Overview

Bring worlds to life with autonomous agents that have goals, memory, personalities, and the ability to interact. This phase transforms static simulations into dynamic, emergent systems where agents make decisions, form relationships, and drive world evolution.

**Key Concept:** Agents with motivations create emergence. Without autonomous actors, simulations remain scripted.

---

## Goals

- ✅ Autonomous agents with goals and strategies
- ✅ Agent decision-making system
- ✅ Relationship dynamics (alliances, conflicts)
- ✅ Conflict and cooperation logic
- ✅ Emergent behavior patterns
- ✅ Agent memory and learning

---

## What We're Building

### 1. Agent Architecture

**Files to Create:**
- `backend/agents/agent.py` - Base agent class
- `backend/agents/agent_types.py` - Specific agent implementations
- `backend/agents/decision_engine.py` - Decision-making logic
- `backend/agents/goal_system.py` - Goal management

**Core Agent Structure:**

```python
class Agent(BaseModel):
    id: str
    world_id: str
    name: str
    type: AgentType
    
    # Core attributes
    goals: List[Goal]
    personality: Personality
    resources: Dict[str, float]
    
    # State
    current_state: AgentState
    memory: AgentMemory
    relationships: Dict[str, Relationship]
    
    # Capabilities
    capabilities: List[str]
    influence: float
    
    def perceive(self, world_state: WorldState) -> Perception:
        """Observe the world"""
        pass
    
    def decide(self, perception: Perception) -> Action:
        """Make decisions based on goals and perception"""
        pass
    
    def act(self, action: Action) -> Result:
        """Execute action in the world"""
        pass
    
    def update_memory(self, event: Event):
        """Store important events"""
        pass
    
    def evaluate_goals(self) -> List[Goal]:
        """Assess goal progress and adjust priorities"""
        pass
```

---

### 2. Agent Types

**Nation Agent:**
```python
class NationAgent(Agent):
    """Represents a country or state"""
    
    economy: float  # 0-100
    military_power: float
    stability: float
    population: int
    territory: List[str]
    government_type: str
    
    def decide_foreign_policy(self) -> ForeignPolicyAction:
        """Decide on alliances, wars, trade"""
        pass
    
    def manage_economy(self) -> EconomicAction:
        """Economic decisions"""
        pass
    
    def respond_to_threat(self, threat: Threat) -> Response:
        """React to external threats"""
        pass
```

**Person Agent:**
```python
class PersonAgent(Agent):
    """Represents an individual"""
    
    role: str
    influence: float
    skills: List[str]
    emotions: EmotionalState
    
    def pursue_career(self) -> CareerAction:
        pass
    
    def form_relationships(self) -> SocialAction:
        pass
    
    def react_emotionally(self, event: Event) -> EmotionalResponse:
        pass
```

**Company Agent:**
```python
class CompanyAgent(Agent):
    """Represents a corporation"""
    
    industry: str
    market_cap: float
    employees: int
    products: List[str]
    
    def expand_market(self) -> BusinessAction:
        pass
    
    def compete(self, rival: CompanyAgent) -> CompetitiveAction:
        pass
    
    def innovate(self) -> Innovation:
        pass
```

**Faction Agent:**
```python
class FactionAgent(Agent):
    """Represents a group with shared ideology"""
    
    ideology: str
    members: int
    influence_areas: List[str]
    
    def recruit(self) -> RecruitmentAction:
        pass
    
    def spread_ideology(self) -> PropagandaAction:
        pass
    
    def organize_action(self) -> CollectiveAction:
        pass
```

---

### 3. Goal System

**Files to Create:**
- `backend/agents/goals.py`
- `backend/agents/goal_planner.py`

**Goal Types:**

```python
class Goal(BaseModel):
    id: str
    description: str
    priority: float  # 0-1
    progress: float  # 0-1
    deadline: Optional[datetime]
    sub_goals: List[Goal]
    
class GoalType(Enum):
    SURVIVAL = "survival"
    POWER = "power"
    WEALTH = "wealth"
    KNOWLEDGE = "knowledge"
    INFLUENCE = "influence"
    SECURITY = "security"
    EXPANSION = "expansion"
    REVENGE = "revenge"
    COOPERATION = "cooperation"

class GoalPlanner:
    def create_plan(self, goal: Goal, world_state: WorldState) -> Plan:
        """Generate action plan to achieve goal"""
        pass
    
    def evaluate_progress(self, goal: Goal, actions: List[Action]) -> float:
        """Measure goal achievement"""
        pass
    
    def adjust_priorities(self, agent: Agent, events: List[Event]):
        """Reprioritize goals based on circumstances"""
        pass
```

**Example Goals:**
```python
# Nation goal
Goal(
    description="Achieve energy independence",
    priority=0.8,
    sub_goals=[
        Goal(description="Build 10 fusion reactors", priority=0.9),
        Goal(description="Reduce oil imports by 50%", priority=0.7)
    ]
)

# Person goal
Goal(
    description="Become CEO",
    priority=0.9,
    sub_goals=[
        Goal(description="Get MBA", priority=0.8),
        Goal(description="Build network", priority=0.7)
    ]
)
```

---

### 4. Decision Engine

**Files to Create:**
- `backend/agents/decision_engine.py`
- `backend/agents/reasoning.py`
- `backend/agents/strategy.py`

**Decision-Making Process:**

```python
class DecisionEngine:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def make_decision(
        self, 
        agent: Agent, 
        situation: Situation,
        options: List[Action]
    ) -> Action:
        """
        Decision-making pipeline:
        1. Perceive situation
        2. Recall relevant memories
        3. Evaluate options against goals
        4. Consider personality traits
        5. Assess risks
        6. Choose action
        """
        
        # Gather context
        context = self._build_context(agent, situation)
        
        # Evaluate each option
        evaluations = []
        for option in options:
            score = self._evaluate_option(
                option, 
                agent.goals, 
                agent.personality,
                context
            )
            evaluations.append((option, score))
        
        # Choose best option
        best_action = max(evaluations, key=lambda x: x[1])[0]
        
        return best_action
    
    def _evaluate_option(
        self, 
        action: Action, 
        goals: List[Goal],
        personality: Personality,
        context: dict
    ) -> float:
        """Score action based on goal alignment and personality"""
        
        # Use LLM for complex reasoning
        prompt = f"""
        Agent personality: {personality}
        Current goals: {goals}
        Proposed action: {action}
        Context: {context}
        
        Rate this action from 0-1 based on:
        - Goal alignment
        - Risk level
        - Personality fit
        - Long-term consequences
        """
        
        score = self.llm.evaluate(prompt)
        return score
```

---

### 5. Relationship System

**Files to Create:**
- `backend/agents/relationships.py`
- `backend/agents/social_dynamics.py`

**Relationship Model:**

```python
class Relationship(BaseModel):
    agent_a: str
    agent_b: str
    type: RelationType
    strength: float  # -1 to 1 (negative = hostile, positive = friendly)
    history: List[Interaction]
    trust: float
    
class RelationType(Enum):
    ALLIANCE = "alliance"
    ENEMY = "enemy"
    TRADE_PARTNER = "trade_partner"
    NEUTRAL = "neutral"
    RIVAL = "rival"
    MENTOR = "mentor"
    SUBORDINATE = "subordinate"

class RelationshipManager:
    def update_relationship(
        self, 
        agent_a: Agent, 
        agent_b: Agent, 
        interaction: Interaction
    ):
        """Modify relationship based on interaction"""
        
        # Positive interactions strengthen bonds
        if interaction.outcome == "positive":
            relationship.strength += 0.1
            relationship.trust += 0.05
        
        # Betrayals damage trust
        elif interaction.type == "betrayal":
            relationship.strength -= 0.3
            relationship.trust -= 0.5
    
    def form_alliance(self, agent_a: Agent, agent_b: Agent) -> Alliance:
        """Create formal alliance"""
        pass
    
    def declare_war(self, agent_a: Agent, agent_b: Agent) -> War:
        """Initiate conflict"""
        pass
```

**Relationship Evolution:**
```
Neutral → Trade Partner → Ally → Close Ally
   ↓
Rival → Enemy → War
```

---

### 6. Conflict & Cooperation Logic

**Files to Create:**
- `backend/agents/conflict_resolver.py`
- `backend/agents/cooperation.py`

**Conflict System:**

```python
class ConflictResolver:
    def resolve_conflict(
        self, 
        agent_a: Agent, 
        agent_b: Agent, 
        conflict: Conflict
    ) -> ConflictOutcome:
        """
        Resolve conflicts based on:
        - Power balance
        - Resources
        - Alliances
        - Strategy
        """
        
        # Calculate power levels
        power_a = self._calculate_power(agent_a)
        power_b = self._calculate_power(agent_b)
        
        # Factor in alliances
        allies_a = self._get_allies(agent_a)
        allies_b = self._get_allies(agent_b)
        
        # Simulate conflict
        outcome = self._simulate_conflict(
            agent_a, power_a, allies_a,
            agent_b, power_b, allies_b
        )
        
        return outcome
    
    def _calculate_power(self, agent: Agent) -> float:
        """Calculate agent's effective power"""
        if isinstance(agent, NationAgent):
            return (
                agent.military_power * 0.4 +
                agent.economy * 0.3 +
                agent.stability * 0.2 +
                agent.influence * 0.1
            )
```

**Cooperation System:**

```python
class CooperationEngine:
    def evaluate_cooperation(
        self, 
        agent_a: Agent, 
        agent_b: Agent,
        proposal: Proposal
    ) -> bool:
        """Determine if agents should cooperate"""
        
        # Check goal alignment
        goal_overlap = self._calculate_goal_overlap(
            agent_a.goals, 
            agent_b.goals
        )
        
        # Check trust level
        relationship = self._get_relationship(agent_a, agent_b)
        
        # Evaluate mutual benefit
        benefit_a = self._evaluate_benefit(agent_a, proposal)
        benefit_b = self._evaluate_benefit(agent_b, proposal)
        
        # Cooperate if mutually beneficial and sufficient trust
        return (
            goal_overlap > 0.5 and
            relationship.trust > 0.6 and
            benefit_a > 0 and
            benefit_b > 0
        )
```

---

### 7. Agent Memory

**Files to Create:**
- `backend/agents/agent_memory.py`

**Memory System:**

```python
class AgentMemory:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.short_term = []  # Recent events (last 10)
        self.long_term = VectorStore()  # All memories
        self.important = []  # High-impact events
    
    def remember(self, event: Event):
        """Store event in memory"""
        
        # Add to short-term
        self.short_term.append(event)
        if len(self.short_term) > 10:
            self.short_term.pop(0)
        
        # Add to long-term with embedding
        self.long_term.add(event)
        
        # Mark important events
        if event.impact > 0.7:
            self.important.append(event)
    
    def recall(self, query: str, k: int = 5) -> List[Event]:
        """Retrieve relevant memories"""
        return self.long_term.query(query, k)
    
    def forget(self, threshold: float):
        """Remove low-importance memories"""
        pass
```

---

### 8. Emergent Behavior

**What We Want to See:**

**Emergent Alliances:**
```
Nation A and B both threatened by Nation C
→ A and B form defensive alliance
→ C seeks allies
→ Arms race begins
```

**Economic Emergence:**
```
Company A innovates
→ Competitors struggle
→ Some adapt, some fail
→ Market consolidation
→ New startups emerge
```

**Social Emergence:**
```
Faction spreads ideology
→ Gains followers
→ Threatens establishment
→ Government cracks down
→ Underground movement forms
```

---

## API Endpoints to Add

```python
# Agent Management
POST   /api/worlds/{id}/agents           # Create agent
GET    /api/worlds/{id}/agents           # List agents
GET    /api/agents/{id}                  # Get agent details
PUT    /api/agents/{id}                  # Update agent
DELETE /api/agents/{id}                  # Remove agent

# Agent Actions
POST   /api/agents/{id}/actions          # Execute action
GET    /api/agents/{id}/actions          # Get action history

# Goals
GET    /api/agents/{id}/goals            # Get agent goals
POST   /api/agents/{id}/goals            # Add goal
PUT    /api/goals/{id}                   # Update goal

# Relationships
GET    /api/agents/{id}/relationships    # Get relationships
POST   /api/relationships                # Create relationship
PUT    /api/relationships/{id}           # Update relationship

# Simulation
POST   /api/worlds/{id}/simulate         # Run simulation step
POST   /api/worlds/{id}/simulate/auto    # Enable auto-simulation
```

---

## Implementation Steps

### Week 5

**Day 1-2: Agent Architecture**
1. Design base Agent class
2. Implement agent types (Nation, Person, Company, Faction)
3. Create agent storage in database
4. Test agent creation and persistence

**Day 3: Goal System**
1. Implement Goal model
2. Create GoalPlanner
3. Add goal evaluation logic
4. Test goal-driven behavior

**Day 4-5: Decision Engine**
1. Build decision-making pipeline
2. Integrate LLM for reasoning
3. Implement option evaluation
4. Test decision quality

### Week 6

**Day 1-2: Relationships**
1. Implement Relationship model
2. Create RelationshipManager
3. Add relationship evolution logic
4. Test alliance/conflict formation

**Day 3: Conflict & Cooperation**
1. Build ConflictResolver
2. Implement CooperationEngine
3. Add power calculation
4. Test conflict outcomes

**Day 4: Agent Memory**
1. Implement AgentMemory
2. Integrate with vector store
3. Add recall functionality
4. Test memory persistence

**Day 5: Integration & Testing**
1. Connect all agent systems
2. Run multi-agent simulations
3. Observe emergent behavior
4. Fix bugs and optimize

---

## Testing Checklist

- [ ] Agents persist across sessions
- [ ] Agents make goal-driven decisions
- [ ] Relationships form and evolve
- [ ] Conflicts resolve realistically
- [ ] Cooperation emerges when beneficial
- [ ] Agent memory stores and recalls events
- [ ] Multiple agents interact simultaneously
- [ ] Emergent patterns appear
- [ ] Performance acceptable with 10+ agents

---

## Success Criteria

**Phase 3 is complete when:**

1. **Autonomous Behavior:**
   - Agents make decisions without manual input
   
2. **Goal-Driven Actions:**
   - Agents pursue goals strategically
   
3. **Relationship Dynamics:**
   - Alliances and conflicts form naturally
   
4. **Emergence:**
   - Unexpected patterns emerge from interactions

**Example Working Scenario:**
```python
# Create world with 3 nations
world = create_world("Geopolitical Sim")

nation_a = NationAgent(
    name="Techland",
    goals=[Goal("Achieve tech dominance")],
    military_power=60
)

nation_b = NationAgent(
    name="Oilstan",
    goals=[Goal("Maintain energy monopoly")],
    military_power=70
)

nation_c = NationAgent(
    name="Neutralia",
    goals=[Goal("Maintain peace")],
    military_power=40
)

# Run simulation
simulate(world, steps=10)

# Observe emergent behavior:
# - Techland and Oilstan become rivals
# - Neutralia forms alliance with Techland
# - Arms race begins
# - Trade wars emerge
```

---

## Known Limitations (To Address in Later Phases)

- ❌ No visualization of agent interactions
- ❌ No emotional evolution
- ❌ No learning from past simulations
- ❌ No multi-agent societies
- ❌ No cultural evolution

---

## Next Phase Preview

**Phase 4** will add:
- Interactive visualization
- Timeline UI
- Simulation dashboard
- Real-time world exploration
- Agent relationship graphs

This will make the simulations explorable and understandable.

---

## Technical Requirements

### New Dependencies

```toml
[project]
dependencies = [
    # Existing...
    
    # Agent simulation
    "networkx>=3.0",  # Relationship graphs
    "numpy>=1.24.0",  # Calculations
    "scipy>=1.11.0",  # Statistical analysis
]
```

---

## Notes

- **Start simple** - Basic agents first, complexity later
- **Test emergence** - Run long simulations to see patterns
- **Balance realism** - Not too simple, not too complex
- **Performance matters** - Optimize decision-making
- **LLM usage** - Use for complex reasoning, not simple logic

**Key Insight:** Agents with goals and memory create worlds that feel alive. This is where the magic happens.
