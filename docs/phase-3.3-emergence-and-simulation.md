# Phase 3.3: Emergence & Automatic Simulation
**Timeline:** Week 6 (Days 3-5)  
**Status:** Not Started  
**Prerequisites:** Phase 3.1 & 3.2 Complete

---

## Overview

The final piece: LLM-powered decision-making and automatic simulation. Agents now make intelligent decisions based on their memory, goals, and relationships. Run simulations automatically and watch emergent patterns appear.

**Key Focus:** This is where the magic happens. Agents with memory + goals + relationships + LLM reasoning = emergent behavior you didn't program.

---

## Goals

- ✅ LLM-powered decision engine
- ✅ Automatic simulation loop
- ✅ Emergent pattern detection
- ✅ Simulation control (step, auto-run, pause)
- ✅ Event propagation system

---

## What We're Building

### 1. Decision Engine with LLM

**File:** `backend/agents/decision_engine.py`

```python
class DecisionEngine:
    """LLM-powered decision-making for agents"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    async def make_decision(
        self,
        db: AsyncSession,
        agent: Agent,
        situation: str,
        available_actions: List[str],
    ) -> Dict[str, Any]:
        """
        Make a decision using LLM reasoning
        
        Process:
        1. Gather context (memory, goals, relationships)
        2. Build prompt with personality
        3. Ask LLM to reason and choose
        4. Parse and validate decision
        """
        # Gather context
        memory_manager = AgentMemoryManager(agent.id)
        goal_manager = GoalManager(agent.id)
        rel_manager = RelationshipManager(agent.id)
        
        memory_context = await memory_manager.build_context(db, situation)
        goal_context = await goal_manager.get_goal_context(db)
        relationship_context = await rel_manager.get_relationship_context(db)
        
        # Build decision prompt
        prompt = self._build_decision_prompt(
            agent=agent,
            situation=situation,
            available_actions=available_actions,
            memory_context=memory_context,
            goal_context=goal_context,
            relationship_context=relationship_context,
        )
        
        # Get LLM decision
        decision = await self.llm.generate_structured(
            prompt=prompt,
            response_model=AgentDecision,
        )
        
        # Store decision as memory
        await memory_manager.remember(
            db,
            memory_type="decision",
            content=f"Decided to: {decision.action}. Reasoning: {decision.reasoning}",
            importance=0.7,
            emotional_valence=decision.confidence - 0.5,  # High confidence = positive
        )
        
        return decision
    
    def _build_decision_prompt(
        self,
        agent: Agent,
        situation: str,
        available_actions: List[str],
        memory_context: str,
        goal_context: str,
        relationship_context: str,
    ) -> str:
        """Build comprehensive decision prompt"""
        
        personality_desc = self._describe_personality(agent.personality)
        
        prompt = f"""
You are {agent.name}, a {agent.agent_type} agent with the role: {agent.role}.

PERSONALITY:
{personality_desc}

CURRENT SITUATION:
{situation}

YOUR MEMORY:
{memory_context}

YOUR GOALS:
{goal_context}

YOUR RELATIONSHIPS:
{relationship_context}

AVAILABLE ACTIONS:
{chr(10).join(f"- {action}" for action in available_actions)}

Based on your personality, memories, goals, and relationships, what should you do?

Think step by step:
1. What do you remember about similar situations?
2. Which goals does this situation affect?
3. How will each action affect your relationships?
4. What are the risks and benefits?
5. What action best fits your personality and goals?

Choose one action and explain your reasoning.
"""
        return prompt
    
    def _describe_personality(self, personality: dict) -> str:
        """Convert personality traits to description"""
        traits = []
        
        if personality.get("ambition", 0.5) > 0.7:
            traits.append("highly ambitious")
        if personality.get("risk_tolerance", 0.5) > 0.7:
            traits.append("risk-taking")
        elif personality.get("risk_tolerance", 0.5) < 0.3:
            traits.append("cautious")
        if personality.get("empathy", 0.5) > 0.7:
            traits.append("empathetic")
        elif personality.get("empathy", 0.5) < 0.3:
            traits.append("ruthless")
        if personality.get("rationality", 0.5) > 0.7:
            traits.append("highly rational")
        elif personality.get("rationality", 0.5) < 0.3:
            traits.append("emotional")
        
        return "You are " + ", ".join(traits) + "."


class AgentDecision(BaseModel):
    """Structured decision output"""
    action: str = Field(..., description="The chosen action")
    reasoning: str = Field(..., description="Why this action was chosen")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in decision")
    expected_outcome: str = Field(..., description="What you expect to happen")
    risks: List[str] = Field(default_factory=list, description="Potential risks")
```

---

### 2. Simulation Engine

**File:** `backend/simulation/simulation_engine.py`

```python
class SimulationEngine:
    """Runs automatic simulation"""
    
    def __init__(self):
        self.decision_engine = DecisionEngine()
        self.running = False
    
    async def simulate_step(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> SimulationStep:
        """
        Run one simulation step
        
        Process:
        1. Get all active agents
        2. Each agent perceives world
        3. Each agent makes decision
        4. Execute actions
        5. Update world state
        6. Detect emergent patterns
        """
        # Get agents
        agent_repo = AgentRepository(db)
        agents = await agent_repo.list_agents(project_id=project_id)
        
        if not agents:
            return SimulationStep(
                step_number=0,
                actions=[],
                events=[],
                patterns=[],
            )
        
        # Get current world state
        world_manager = WorldManager(db)
        world_state = await world_manager.get_world_state(project_id)
        
        step_actions = []
        step_events = []
        
        # Each agent acts
        for agent in agents:
            # Build situation description
            situation = self._describe_situation(world_state, agent)
            
            # Get available actions for this agent type
            available_actions = self._get_available_actions(agent)
            
            # Agent decides
            decision = await self.decision_engine.make_decision(
                db,
                agent=agent,
                situation=situation,
                available_actions=available_actions,
            )
            
            # Execute action
            result = await self._execute_action(
                db,
                agent=agent,
                decision=decision,
                world_state=world_state,
            )
            
            step_actions.append({
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "action": decision.action,
                "reasoning": decision.reasoning,
                "result": result,
            })
            
            # Generate events from action
            events = self._generate_events(agent, decision, result)
            step_events.extend(events)
        
        # Detect emergent patterns
        patterns = await self._detect_patterns(db, project_id, step_events)
        
        return SimulationStep(
            step_number=1,  # Will be tracked properly
            actions=step_actions,
            events=step_events,
            patterns=patterns,
        )
    
    def _describe_situation(
        self,
        world_state: WorldState,
        agent: Agent,
    ) -> str:
        """Describe current situation for agent"""
        if not world_state or not world_state.state:
            return "The world is in its initial state."
        
        state = world_state.state
        
        # Build situation description
        parts = ["Current world state:"]
        
        for key, value in state.items():
            parts.append(f"- {key}: {value}")
        
        # Add agent-specific context
        parts.append(f"\nYou are {agent.name}, {agent.role}.")
        
        return "\n".join(parts)
    
    def _get_available_actions(self, agent: Agent) -> List[str]:
        """Get actions available to this agent type"""
        
        # Base actions for all agents
        base_actions = [
            "observe and wait",
            "gather information",
            "build relationships",
        ]
        
        # Type-specific actions
        if agent.agent_type == "ceo":
            return base_actions + [
                "expand business operations",
                "launch new product",
                "acquire competitor",
                "form strategic partnership",
                "cut costs and optimize",
                "invest in R&D",
            ]
        elif agent.agent_type == "policy":
            return base_actions + [
                "propose new policy",
                "negotiate with other nations",
                "increase military spending",
                "invest in infrastructure",
                "form alliance",
                "impose sanctions",
            ]
        elif agent.agent_type == "personal":
            return base_actions + [
                "pursue career advancement",
                "start new project",
                "help others",
                "seek revenge",
                "build influence",
                "learn new skills",
            ]
        else:
            return base_actions + [
                "take initiative",
                "collaborate with others",
                "compete for resources",
                "innovate",
            ]
    
    async def _execute_action(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: WorldState,
    ) -> str:
        """Execute agent's chosen action"""
        
        # Simple execution for now
        # In a full implementation, this would:
        # - Check if action is valid
        # - Calculate success probability
        # - Update world state
        # - Affect other agents
        # - Generate consequences
        
        # For now, just record the action
        memory_manager = AgentMemoryManager(agent.id)
        await memory_manager.remember(
            db,
            memory_type="observation",
            content=f"I executed: {decision.action}. Expected: {decision.expected_outcome}",
            importance=0.6,
        )
        
        return f"Action '{decision.action}' executed successfully."
    
    def _generate_events(
        self,
        agent: Agent,
        decision: AgentDecision,
        result: str,
    ) -> List[Dict]:
        """Generate world events from agent action"""
        return [{
            "event_type": "agent_action",
            "description": f"{agent.name} decided to: {decision.action}",
            "agent_id": str(agent.id),
            "impact": "low",  # Would be calculated based on action
        }]
    
    async def _detect_patterns(
        self,
        db: AsyncSession,
        project_id: UUID,
        events: List[Dict],
    ) -> List[str]:
        """Detect emergent patterns"""
        patterns = []
        
        # Simple pattern detection
        # In full implementation, use ML or LLM to detect:
        # - Alliance formations
        # - Arms races
        # - Economic bubbles
        # - Social movements
        # - Cultural shifts
        
        # For now, just count event types
        event_types = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if event_types.get("agent_action", 0) > 5:
            patterns.append("High agent activity detected")
        
        return patterns
    
    async def run_auto_simulation(
        self,
        db: AsyncSession,
        project_id: UUID,
        max_steps: int = 100,
        step_delay: float = 1.0,
    ):
        """Run simulation automatically"""
        self.running = True
        step_count = 0
        
        while self.running and step_count < max_steps:
            # Run one step
            step_result = await self.simulate_step(db, project_id)
            
            logger.info(f"Simulation step {step_count + 1}: {len(step_result.actions)} actions")
            
            step_count += 1
            
            # Delay between steps
            await asyncio.sleep(step_delay)
        
        self.running = False
        logger.info(f"Simulation completed: {step_count} steps")
    
    def stop_simulation(self):
        """Stop automatic simulation"""
        self.running = False


class SimulationStep(BaseModel):
    """Result of one simulation step"""
    step_number: int
    actions: List[Dict]
    events: List[Dict]
    patterns: List[str]
```

---

### 3. Emergence Detection

**File:** `backend/simulation/emergence_detector.py`

```python
class EmergenceDetector:
    """Detects emergent patterns in simulation"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    async def detect_patterns(
        self,
        db: AsyncSession,
        project_id: UUID,
        time_window: int = 10,  # Last N steps
    ) -> List[EmergentPattern]:
        """
        Detect emergent patterns using LLM
        
        Looks for:
        - Alliance formations
        - Conflict escalations
        - Economic trends
        - Social movements
        - Cultural shifts
        """
        # Get recent events
        world_manager = WorldManager(db)
        events = await world_manager.get_events(project_id)
        recent_events = events[:time_window * 10]  # Approximate
        
        # Get recent agent interactions
        # (Would query agent_interactions table)
        
        # Build pattern detection prompt
        prompt = self._build_pattern_prompt(recent_events)
        
        # Ask LLM to identify patterns
        patterns = await self.llm.generate_structured(
            prompt=prompt,
            response_model=EmergentPatterns,
        )
        
        return patterns.patterns
    
    def _build_pattern_prompt(self, events: List) -> str:
        """Build prompt for pattern detection"""
        
        event_descriptions = "\n".join([
            f"- {e.event_type}: {e.description}"
            for e in events[:50]  # Last 50 events
        ])
        
        prompt = f"""
Analyze these recent events and identify emergent patterns:

EVENTS:
{event_descriptions}

Look for:
1. Alliance formations (agents cooperating)
2. Conflict escalations (tensions rising)
3. Economic trends (wealth concentration, market shifts)
4. Social movements (ideology spreading)
5. Power shifts (influence changing)

Identify any emergent patterns that weren't explicitly programmed.
"""
        return prompt


class EmergentPattern(BaseModel):
    """An emergent pattern detected in simulation"""
    pattern_type: str = Field(..., description="Type of pattern")
    description: str = Field(..., description="What is happening")
    involved_agents: List[str] = Field(default_factory=list)
    significance: float = Field(..., ge=0.0, le=1.0)


class EmergentPatterns(BaseModel):
    """Collection of patterns"""
    patterns: List[EmergentPattern]
```

---

## API Endpoints

```python
# Simulation Control
POST   /api/projects/{id}/simulate/step     # Run one step
POST   /api/projects/{id}/simulate/start    # Start auto-simulation
POST   /api/projects/{id}/simulate/stop     # Stop simulation
GET    /api/projects/{id}/simulate/status   # Get simulation status

# Emergence
GET    /api/projects/{id}/patterns          # Get emergent patterns
GET    /api/projects/{id}/simulation/history # Get simulation history
```

---

## Implementation Checklist

### Day 3: Decision Engine
- [ ] Create decision_engine.py
- [ ] Implement LLM-powered decision-making
- [ ] Add decision prompt building
- [ ] Test decision quality

### Day 4: Simulation Engine
- [ ] Create simulation_engine.py
- [ ] Implement simulate_step()
- [ ] Implement run_auto_simulation()
- [ ] Add simulation control API

### Day 5: Emergence & Testing
- [ ] Create emergence_detector.py
- [ ] Implement pattern detection
- [ ] Run multi-step simulations
- [ ] Observe emergent behavior
- [ ] Document patterns found

---

## Success Criteria

Phase 3.3 is complete when:

1. **Agents Decide Intelligently:**
   - LLM makes context-aware decisions
   - Decisions consider memory, goals, relationships
   - Decisions match personality

2. **Simulation Runs:**
   - Can run step-by-step
   - Can run automatically
   - Can pause/resume

3. **Emergence Appears:**
   - Unexpected patterns emerge
   - Alliances form naturally
   - Conflicts escalate organically
   - Social dynamics evolve

---

## Example Emergent Patterns

**Alliance Formation:**
```
Step 1: Nation A and B both threatened by C
Step 5: A and B start cooperating
Step 10: Formal alliance formed
Step 15: Joint military exercises
→ Emergent: Defensive alliance against common threat
```

**Economic Bubble:**
```
Step 1: Company A innovates
Step 3: Competitors copy
Step 7: Market saturates
Step 12: Prices collapse
Step 15: Consolidation begins
→ Emergent: Boom-bust cycle
```

**Social Movement:**
```
Step 1: Faction spreads ideology
Step 5: Gains followers
Step 10: Threatens establishment
Step 15: Government cracks down
Step 20: Underground resistance
→ Emergent: Revolution brewing
```

---

## Phase 3 Complete!

When Phase 3.3 is done, you have:
- ✅ Autonomous agents with memory
- ✅ Goal-driven behavior
- ✅ Dynamic relationships
- ✅ LLM-powered decisions
- ✅ Automatic simulation
- ✅ Emergent patterns

**This is a living, breathing world!** 🌍✨

Next: Phase 4 (Visualization) to see it all in action!
