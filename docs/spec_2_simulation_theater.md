# 🎭 Spec Sheet 2: The Simulation Theater

> *"Every simulation is a story waiting to be told."*

## The Problem

Right now, simulations run as dry API calls: `POST /simulate/step` → get JSON → repeat. The user has to manually interpret raw action data, mentally track agent arcs, and figure out when something interesting happened.

**The Simulation Theater** transforms raw simulation output into a **living narrative** — with auto-pacing, dramatic tension tracking, divergence point detection, mid-simulation interventions, and story-quality summaries.

---

## Core Concept: The Director's Chair

The user sits in the **Director's Chair**. They set the stage (via the Seeder), then watch the simulation unfold. But unlike a passive audience, they can:

1. **🎬 Auto-Direct** — Let the system pace itself, speeding through calm phases and pausing at dramatic moments
2. **🔀 Branch** — When a pivotal moment occurs, fork the timeline and explore "what if they'd chosen differently?"
3. **💉 Inject** — Throw a curveball mid-simulation ("A whistleblower leaks everything to the press")
4. **📖 Narrate** — Get each step as a story beat, not a JSON blob

```
┌─────────────────────────────────────────────────┐
│                SIMULATION THEATER                │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │  Seeder  │───▶│ Director │───▶│ Narrator │   │
│  │ (Spec 1) │    │          │    │          │   │
│  └──────────┘    └────┬─────┘    └────┬─────┘   │
│                       │               │          │
│              ┌────────▼────────┐      │          │
│              │  SimulationEngine│      │          │
│              │  (existing)      │◀─────┘          │
│              └────────┬────────┘                 │
│                       │                          │
│         ┌─────────────▼─────────────┐            │
│         │    Tension Tracker        │            │
│         │  ┌─────┐ ┌──────┐ ┌────┐ │            │
│         │  │Pace │ │Branch│ │Inj.│ │            │
│         │  │Ctrl │ │Detect│ │Gate│ │            │
│         │  └─────┘ └──────┘ └────┘ │            │
│         └───────────────────────────┘            │
└─────────────────────────────────────────────────┘
```

---

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `backend/theater/simulation_theater.py` | **[NEW]** Main orchestrator — the Theater |
| `backend/theater/tension_tracker.py` | **[NEW]** Tracks dramatic tension across steps |
| `backend/theater/narrative_director.py` | **[NEW]** LLM-powered narrative summaries |
| `backend/theater/divergence_detector.py` | **[NEW]** Detects branch-worthy moments |
| `backend/theater/event_injector.py` | **[NEW]** Handles mid-simulation event injection |
| `backend/theater/pacing_engine.py` | **[NEW]** Auto-pacing logic |
| `backend/theater/theater_models.py` | **[NEW]** Pydantic models for theater I/O |
| `backend/api/theater.py` | **[NEW]** API endpoints for the Theater |

### Modified Files

| File | Change |
|------|--------|
| `backend/main.py` | Mount `/api/theater` router |
| `backend/simulation/simulation_engine.py` | Add hooks for tension tracking & event injection |
| `backend/api/simulation.py` | Add SSE streaming endpoint |

---

## Feature 1: The Tension Tracker

Every step of the simulation produces data that can be scored for **dramatic tension**. The Tension Tracker computes a real-time "drama score" that drives pacing and divergence detection.

### Tension Metrics

```python
class TensionMetrics(BaseModel):
    """Real-time dramatic tension measurement."""
    
    step: int
    overall_tension: float           # 0-1 composite score
    
    # Component scores
    conflict_intensity: float        # How hostile are agent interactions?
    stakes_level: float              # How much is at risk? (resources, reputation)
    uncertainty: float               # How unpredictable is the outcome?
    momentum_shift: float            # Did power dynamics change this step?
    relationship_volatility: float   # Are alliances forming/breaking?
    
    # Narrative markers
    is_climax_candidate: bool        # Tension > 0.8 for 2+ consecutive steps
    is_lull: bool                    # Tension < 0.3 for 2+ consecutive steps
    phase: str                       # "rising_action", "climax", "falling_action", "resolution"
    
    # What's driving the tension
    tension_sources: List[str]       # ["Marcus's sabotage attempt", "Elena's media campaign"]
```

### How Tension Is Calculated

```python
class TensionTracker:
    def compute_tension(
        self,
        actions_this_step: List[ActionResponse],
        world_state: StructuredWorldState,
        patterns: List[EmergentPattern],
        history: List[TensionMetrics],
    ) -> TensionMetrics:
        """
        Compute dramatic tension from step results.
        
        Scoring:
        - Conflict intensity: count of attack/sabotage/expose actions
        - Stakes level: magnitude of resource/reputation changes
        - Uncertainty: variance in agent confidence scores
        - Momentum shift: delta in power rankings between steps
        - Relationship volatility: new alliances or broken rivalries
        """
```

### Tension Arc Visualization

The tracker maintains a **tension arc** — a time series of tension scores across all steps:

```
Tension
  1.0 │                    ╱╲
      │                   ╱  ╲      ← Climax
  0.8 │              ╱╲  ╱    ╲
      │             ╱  ╲╱      ╲
  0.6 │        ╱╲  ╱            ╲
      │       ╱  ╲╱              ╲
  0.4 │   ╱╲ ╱                    ╲
      │  ╱  ╲                      ╲
  0.2 │ ╱                           ╲
      │╱                             ╲
  0.0 └──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──
         1  2  3  4  5  6  7  8  9  10
                    Step
         |--intel--|--execution---|--res-|
```

---

## Feature 2: Auto-Pacing Engine

Instead of running all steps at the same speed, the Pacing Engine adjusts based on tension:

```python
class PacingEngine:
    """Adjusts simulation speed based on dramatic tension."""
    
    class PacingMode(Enum):
        MANUAL = "manual"           # User clicks "next step"
        AUTO_UNIFORM = "uniform"     # Fixed delay between steps
        AUTO_DRAMATIC = "dramatic"   # Speed varies with tension
    
    async def get_pacing_recommendation(
        self,
        tension: TensionMetrics,
        history: List[TensionMetrics],
    ) -> PacingRecommendation:
        """
        Returns:
        - delay_seconds: how long to wait before next step
        - should_pause: whether to pause for user attention
        - reason: why this pacing was chosen
        """
```

### Pacing Rules

| Tension Level | Behavior | Delay |
|--------------|----------|-------|
| < 0.2 (lull) | Fast-forward, minimal narration | 0.5s |
| 0.2 - 0.5 (rising) | Normal pace, standard narration | 2s |
| 0.5 - 0.8 (high) | Slow down, detailed narration | 4s |
| > 0.8 (climax) | **PAUSE** — ask user if they want to branch | ∞ (wait) |
| Phase transition | **PAUSE** — announce phase change | ∞ (wait) |

---

## Feature 3: Divergence Point Detection

A **Divergence Point** is a moment where the simulation reaches a critical juncture — a point where a different choice would lead to a dramatically different outcome. The system detects these automatically.

```python
class DivergenceDetector:
    """Detects moments where timeline branching would be most interesting."""
    
    def detect_divergence(
        self,
        actions_this_step: List[ActionResponse],
        tension: TensionMetrics,
        world_state: StructuredWorldState,
        patterns: List[EmergentPattern],
    ) -> Optional[DivergencePoint]:
        """
        A divergence point is triggered when:
        1. A high-stakes action barely succeeded or barely failed
        2. Two agents chose opposing actions in the same step
        3. A tipping point was reached (regulatory investigation, alliance break)
        4. An agent's dramatic function shifted (ally became enemy)
        5. Tension has been rising for 3+ steps (climax approaching)
        """
```

```python
class DivergencePoint(BaseModel):
    step: int
    description: str                 # "Marcus's sabotage of TechCorp's supply chain"
    significance: float              # 0-1
    
    # What-if branches the user can explore
    branches: List[DivergenceBranch]
    
    # State snapshot for branch recreation
    world_state_snapshot: Dict
    agent_states_snapshot: Dict

class DivergenceBranch(BaseModel):
    label: str                       # "What if the sabotage had failed?"
    description: str                 # "TechCorp's security catches the attempt"
    modifications: Dict              # What to change in the world state
    estimated_impact: str            # "Marcus faces retaliation, Elena gains evidence"
```

### Branching API

```
POST /api/theater/{project_id}/branch
```

```json
{
  "divergence_point_step": 5,
  "branch_label": "What if the sabotage failed?",
  "modifications": {
    "actions": {
      "marcus_rivera": { "success": false, "outcome": "Security caught the attempt" }
    },
    "world_state": {
      "agent_exposure": { "marcus_rivera": 0.7 }
    }
  }
}
```

This creates a **new timeline** (using the existing Timeline system) with a forked world state, then continues the simulation from the divergence point.

---

## Feature 4: What-If Injection

Users can inject **external events** into a running simulation — curveballs that disrupt agent plans and create new dynamics.

```python
class EventInjector:
    """Injects external events into a running simulation."""
    
    async def inject(
        self,
        db: AsyncSession,
        project_id: UUID,
        event: InjectedEvent,
    ) -> InjectionResult:
        """
        Inject an event that:
        1. Modifies world state (market crash, regulation, leak)
        2. Creates discovery memories for affected agents
        3. Forces cooldown resets (new situation = new actions needed)
        4. Is visible to agents in next step's _describe_situation()
        """
```

```python
class InjectedEvent(BaseModel):
    description: str                 # "A major data breach at TechCorp is leaked to the press"
    event_type: str                  # "scandal", "market_crash", "discovery", "regulation", etc.
    
    # Effects (user can specify, or LLM will auto-determine)
    world_state_changes: Optional[Dict]   # null = let LLM decide
    affected_agents: Optional[List[str]]  # null = let LLM decide
    visibility: float                     # 0-1 (how public is this event?)
    
    # Narrative
    source: str                      # "user_injection" or "system_wildcard"
```

### Pre-Built Injections (Quick Actions)

The Theater offers pre-built injection templates:

| Template | Effect |
|----------|--------|
| 🌋 **Market Crash** | All market conditions -0.3, resource drain |
| 📰 **Media Leak** | Target agent's exposure +0.5, media attention +0.4 |
| ⚖️ **Regulatory Crackdown** | Regulatory pressure +0.5 on target sector |
| 🤝 **Forced Alliance** | Two agents must cooperate (trust +0.3) |
| 💣 **Whistleblower** | Specific hidden fact is revealed to ALL agents |
| 🎲 **Wildcard** | LLM generates a random disruptive event |

---

## Feature 5: Narrative Director

The **Narrative Director** transforms raw step data into **story-quality prose**. Every step becomes a chapter in the simulation's unfolding story.

```python
class NarrativeDirector:
    """Transforms simulation data into compelling narratives."""
    
    async def narrate_step(
        self,
        step: int,
        actions: List[ActionResponse],
        tension: TensionMetrics,
        world_state: StructuredWorldState,
        previous_narrative: Optional[str],
    ) -> StepNarrative:
        """
        Generate a narrative summary of what happened this step.
        
        The LLM receives:
        - What each agent did and why
        - The tension metrics
        - Previous narrative (for continuity)
        - The current phase (intel/execution/climax)
        
        Output is structured prose, not a list of actions.
        """
```

```python
class StepNarrative(BaseModel):
    step: int
    phase: str                       # "intel", "execution", "climax", "resolution"
    headline: str                    # "The Gloves Come Off"
    summary: str                     # 2-3 paragraph narrative summary
    
    # Per-agent story beats
    agent_beats: List[AgentBeat]
    
    # Dramatic questions raised
    open_questions: List[str]        # "Will Elena's evidence be enough?"
    
    # Foreshadowing (from LLM analysis)
    foreshadowing: Optional[str]     # "Marcus's aggressive move may backfire..."

class AgentBeat(BaseModel):
    agent_name: str
    action_summary: str              # "Sarah moved to secure her supply chain"
    motivation_insight: str          # "Driven by the patent expiry deadline"
    emotional_state: str             # "anxious", "confident", "desperate"
```

### Example Output

```
═══════════════════════════════════════════
  Chapter 4: "The Gloves Come Off"
  Phase: EXECUTION  |  Tension: 0.72 ▲
═══════════════════════════════════════════

After three rounds of careful intelligence gathering, the players 
finally showed their hands.

Sarah Chen, armed with the knowledge that TechCorp's patent expires 
in 18 months, moved aggressively to lock down an exclusive supplier 
agreement in Vietnam — cutting off RivalCorp's access to critical 
components. A calculated gamble from someone running out of time.

Marcus Rivera, meanwhile, had been planning something far more 
audacious. Using the intelligence his operatives had gathered about 
TechCorp's single-supplier dependency, he launched a hostile bid to 
acquire the Vietnamese supplier outright. The two CEOs were now on 
a collision course.

But it was Elena Rodriguez who made the most consequential move of 
all. Having connected TechCorp's illegal coolant dumping with the 
California class-action lawsuit, she quietly briefed a New York 
Times journalist. The story would break in the morning.

  ⚡ DIVERGENCE POINT DETECTED
  "What if Elena's story doesn't run? The journalist gets cold feet."
  
  [Branch Timeline] [Continue] [Inject Event]
```

---

## Feature 6: Full Story Compilation

After a simulation completes (or is stopped), the Narrative Director compiles a **full story document**:

```python
class StoryCompiler:
    async def compile(
        self,
        project_id: UUID,
        narratives: List[StepNarrative],
        dna: ScenarioDNA,
        tension_arc: List[TensionMetrics],
    ) -> SimulationStory:
        """
        Compile all step narratives into a cohesive story with:
        - Prologue (from scenario DNA)
        - Chapters (from step narratives)
        - Epilogue (LLM-generated conclusion)
        - Character arcs (how each agent evolved)
        - Themes explored
        - "What we learned" section
        """
```

```python
class SimulationStory(BaseModel):
    title: str
    prologue: str                    # Sets the scene
    chapters: List[StepNarrative]    # The story
    epilogue: str                    # LLM-generated conclusion
    
    # Analysis
    character_arcs: List[CharacterArc]  # How each agent evolved
    themes_explored: List[str]          # What the simulation revealed
    key_insights: List[str]             # "What we learned about AGI governance"
    
    # Meta
    tension_arc: List[float]            # Tension scores over time
    total_actions: int
    total_patterns: int
    timelines_explored: int

class CharacterArc(BaseModel):
    agent_name: str
    role: str
    starting_position: str           # "Dominant market leader"
    ending_position: str             # "Under regulatory investigation"
    key_moments: List[str]           # Turning points in their arc
    arc_type: str                    # "tragic_fall", "rise_to_power", "redemption", etc.
```

---

## API Design

### Theater Session Endpoints

```
# Start a theater session (wraps simulation with narrative + pacing)
POST /api/theater/{project_id}/start
{
  "pacing_mode": "dramatic",     // "manual", "uniform", "dramatic"
  "narration_style": "cinematic", // "cinematic", "journalistic", "analytical"
  "enable_divergence_detection": true,
  "enable_wildcards": false,      // auto-inject random events?
  "max_steps": 12
}

# Get current theater state (tension, narrative, divergence points)
GET /api/theater/{project_id}/state

# Advance one step (manual mode)
POST /api/theater/{project_id}/next

# Inject an event
POST /api/theater/{project_id}/inject
{ "description": "Market crash triggered by AI stock bubble", "event_type": "market_crash" }

# Branch at a divergence point
POST /api/theater/{project_id}/branch
{ "divergence_point_step": 5, "branch_label": "What if...", "modifications": {} }

# Get full story
GET /api/theater/{project_id}/story

# Stream events in real-time (SSE)
GET /api/theater/{project_id}/stream
```

### Server-Sent Events (SSE) Stream

For real-time frontend updates, the Theater provides an SSE stream:

```
GET /api/theater/{project_id}/stream
```

Events emitted:
```
event: step_start
data: {"step": 4, "phase": "execution"}

event: agent_action
data: {"agent": "Sarah Chen", "action": "secure supply chain", "success": true}

event: tension_update
data: {"tension": 0.72, "phase": "rising_action", "is_climax_candidate": false}

event: narrative
data: {"headline": "The Gloves Come Off", "summary": "After three rounds..."}

event: divergence_point
data: {"step": 5, "description": "Elena's media leak", "branches": [...]}

event: simulation_complete
data: {"total_steps": 10, "story_available": true}
```

---

## Integration with Spec 1 (Scenario Seeder)

The complete flow from prompt to story:

```
User: "What if AGI is achieved by 2029?"
  │
  ├── POST /api/seed/generate          ← Spec 1
  │   └── Returns seed preview
  │
  ├── PUT /api/seed/{id}/remix         ← Spec 1 (optional)
  │   └── User tweaks agents/goals
  │
  ├── POST /api/seed/{id}/commit       ← Spec 1
  │   └── Creates project + world
  │
  ├── POST /api/theater/{id}/start     ← Spec 2
  │   └── Begins theatrical simulation
  │
  ├── GET /api/theater/{id}/stream     ← Spec 2
  │   └── Real-time narrative updates
  │
  ├── POST /api/theater/{id}/inject    ← Spec 2 (optional)
  │   └── User throws a curveball
  │
  ├── POST /api/theater/{id}/branch    ← Spec 2 (optional)
  │   └── Fork at divergence point
  │
  └── GET /api/theater/{id}/story      ← Spec 2
      └── Full compiled narrative
```

Or the **one-shot** express lane:

```
User: "What if AGI is achieved by 2029?"
  │
  └── POST /api/seed/quick-launch      ← Spec 1+2 combined
      ├── auto_simulate: true
      ├── pacing: "dramatic"
      └── Returns project_id + stream URL
```

---

## Implementation Order

1. **`theater_models.py`** — Define TensionMetrics, StepNarrative, DivergencePoint, etc.
2. **`tension_tracker.py`** — Tension computation (no LLM needed, pure math)
3. **`pacing_engine.py`** — Pacing rules (simple logic)
4. **`narrative_director.py`** — LLM-powered narration (needs prompt engineering)
5. **`divergence_detector.py`** — Branch detection logic
6. **`event_injector.py`** — Mid-simulation event injection
7. **`simulation_theater.py`** — Orchestrator that chains everything
8. **`api/theater.py`** — API endpoints + SSE streaming
9. **Integration** — Hook tension tracker into `simulation_engine.py`
10. **`story_compiler.py`** — Post-simulation story generation

---

## Success Criteria

- [ ] Theater session produces a narrative for every step (not just JSON)
- [ ] Tension tracker correctly identifies climax moments (high-stakes actions)
- [ ] Auto-pacing pauses at dramatic moments, fast-forwards through lulls
- [ ] At least 1 divergence point detected per 10-step simulation
- [ ] Event injection successfully disrupts agent behavior in subsequent steps
- [ ] Timeline branching creates a separate project fork from divergence point
- [ ] Full story compilation produces a coherent narrative with character arcs
- [ ] SSE stream delivers real-time updates to frontend
- [ ] End-to-end flow from Seeder → Theater works in one seamless pipeline
