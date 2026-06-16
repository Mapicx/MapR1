# 🧬 Spec Sheet 1: The Scenario Seeder

> *"Give me a premise. I'll give you a world."*

## The Problem

Today, running a MapR1 simulation requires **6+ manual API calls** — creating a project, world state, agents (each with carefully tuned personalities), goals, and entity relationships. This is tedious, error-prone, and kills the magic of "what if?" exploration.

**The Scenario Seeder** is an LLM-powered auto-generation pipeline that takes a single user prompt and produces a **fully wired simulation world** — ready to run — in one shot.

---

## Core Concept: Scenario DNA

Every "what if?" prompt contains implicit **DNA** — conflicts, power dynamics, factions, and tensions waiting to unfold. The Seeder's job is to **extract that DNA** and express it as a living simulation.

```
User Prompt: "What if AGI is achieved by 2029?"
                    │
                    ▼
        ┌─── Scenario DNA Extraction ───┐
        │  Themes: [technology, power,   │
        │    existential risk, economics]│
        │  Core Tension: control vs.     │
        │    open access                 │
        │  Factions: [builders, govts,   │
        │    activists, public]          │
        │  Time Horizon: 2024-2035       │
        └───────────┬───────────────────┘
                    │
        ┌───────────▼───────────────────┐
        │     Multi-Pass Generation      │
        │  Pass 1: World Fabric          │
        │  Pass 2: Entity Graph          │
        │  Pass 3: Agent Casting         │
        │  Pass 4: Goal & Knowledge Web  │
        │  Pass 5: Tension Wiring        │
        └───────────┬───────────────────┘
                    │
                    ▼
          🌍 Complete Simulation World
             Ready to run.
```

---

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `backend/seeder/scenario_seeder.py` | **[NEW]** Main orchestrator — the Seeder pipeline |
| `backend/seeder/dna_extractor.py` | **[NEW]** Pass 0 — Extract Scenario DNA from prompt |
| `backend/seeder/world_fabricator.py` | **[NEW]** Pass 1 — Generate world state & conditions |
| `backend/seeder/entity_generator.py` | **[NEW]** Pass 2 — Generate entities & entity relationships |
| `backend/seeder/agent_caster.py` | **[NEW]** Pass 3 — Cast agents with personalities |
| `backend/seeder/goal_weaver.py` | **[NEW]** Pass 4 — Assign goals & seed hidden knowledge |
| `backend/seeder/tension_wirer.py` | **[NEW]** Pass 5 — Wire up agent relationships & rivalries |
| `backend/seeder/seed_models.py` | **[NEW]** Pydantic models for seeder I/O |
| `backend/api/seeder.py` | **[NEW]** API endpoints for auto-generation |

### Modified Files

| File | Change |
|------|--------|
| `backend/main.py` | Mount new `/api/seed` router |
| `backend/agents/world_knowledge.py` | Add method to register scenario-specific hidden facts |

---

## The 5-Pass Generation Pipeline

### Pass 0 — DNA Extraction (`dna_extractor.py`)

The first LLM call analyzes the user's prompt and extracts structured "Scenario DNA":

```python
class ScenarioDNA(BaseModel):
    """The genetic code of a scenario — everything needed to build a world."""

    # Core identity
    title: str                          # "The AGI Race"
    premise: str                        # 1-paragraph scenario description
    time_horizon: Tuple[int, int]       # (2024, 2035)

    # Thematic structure
    primary_themes: List[str]           # ["technology", "power", "existential_risk"]
    core_tension: str                   # "Who controls AGI — corporations, governments, or no one?"
    secondary_tensions: List[str]       # ["open-source vs proprietary", "safety vs speed"]

    # Faction blueprint
    factions: List[FactionBlueprint]    # [{name, archetype, motivation, stance_on_core_tension}]
    
    # World conditions
    starting_conditions: Dict[str, str] # {"economy": "booming", "geopolitics": "tense"}
    key_variables: List[str]            # ["AGI capability level", "public trust in AI"]
    
    # Narrative seeds
    inciting_incidents: List[str]       # Events that kick off the scenario
    potential_wildcards: List[str]      # Unpredictable events that could happen
    
    # Complexity settings
    recommended_agent_count: int        # 3-8 (LLM estimates ideal count)
    recommended_step_count: int         # 6-20 (how many sim steps for full arc)
    intensity: float                    # 0-1 (how volatile the scenario is)
```

```python
class FactionBlueprint(BaseModel):
    name: str                           # "The Builders"
    archetype: str                      # "technology_company"
    motivation: str                     # "Be first to achieve AGI"
    stance_on_core_tension: str         # "Corporate control, proprietary access"
    key_resource: str                   # "talent, compute, funding"
    vulnerability: str                  # "public backlash, regulation"
```

**Why this matters**: Instead of asking the LLM to generate everything at once (which produces generic, shallow results), we first extract the **conflict structure**. This gives every subsequent pass a thematic spine to build on.

---

### Pass 1 — World Fabric (`world_fabricator.py`)

Generates the initial `StructuredWorldState` from the DNA:

```python
class WorldFabricator:
    async def fabricate(
        self, 
        dna: ScenarioDNA,
        user_overrides: Optional[Dict] = None,
    ) -> StructuredWorldState:
        """
        Generate initial world conditions from scenario DNA.
        
        Produces:
        - Market conditions per relevant sector
        - Public opinion on key themes
        - Media attention distribution
        - Regulatory pressure levels
        - Initial resources/power distribution
        """
```

**Output example** for "AGI by 2029":
```json
{
  "market_conditions": {
    "ai_compute": 0.9,
    "traditional_tech": 0.6,
    "healthcare": 0.5,
    "defense": 0.7
  },
  "public_opinion": {
    "ai_safety": 0.3,
    "corporate_ai": -0.2,
    "government_regulation": 0.4
  },
  "media_attention": {
    "ai_breakthroughs": 0.8,
    "ai_safety": 0.5,
    "job_displacement": 0.6
  },
  "regulatory_pressure": {
    "ai_industry": 0.4
  }
}
```

---

### Pass 2 — Entity Graph (`entity_generator.py`)

Generates entities (companies, nations, organizations) from the faction blueprints:

```python
class EntityGenerator:
    async def generate(
        self,
        dna: ScenarioDNA,
        user_overrides: Optional[List[EntityOverride]] = None,
    ) -> List[EntitySeed]:
        """
        For each faction in the DNA, generate 1+ concrete entities.
        
        A faction like "The Builders" might produce:
        - DeepMind (company, archetype: tech_giant)
        - Prometheus Labs (company, archetype: ai_startup)
        
        Also generates entity-to-entity relationships:
        - DeepMind ←rival→ Prometheus Labs
        - DeepMind ←trade_partner→ UK Government
        """
```

```python
class EntitySeed(BaseModel):
    name: str
    type: str               # "company", "nation", "faction", "person"
    faction: str             # Which faction blueprint it belongs to
    description: str
    attributes: Dict         # Sector, size, influence level, etc.
    
class EntityRelationshipSeed(BaseModel):
    entity_a: str            # Name reference
    entity_b: str            # Name reference
    relationship_type: str   # "rival", "alliance", "trade_partner", etc.
    strength: str            # "weak", "medium", "strong"
    description: str
```

---

### Pass 3 — Agent Casting (`agent_caster.py`)

This is where the magic happens. The LLM "casts" agents like a film director casts actors — each agent is designed to **create maximum dramatic tension** based on the scenario DNA.

```python
class AgentCaster:
    async def cast(
        self,
        dna: ScenarioDNA,
        entities: List[EntitySeed],
        user_overrides: Optional[List[AgentOverride]] = None,
    ) -> List[AgentSeed]:
        """
        Cast agents that embody the scenario's tensions.
        
        Rules:
        1. Every core tension must have agents on BOTH sides
        2. At least one agent should be a "wildcard" (unpredictable)
        3. Personalities should create natural friction
        4. Agent types should be diverse (not all CEOs)
        5. Each agent needs a clear "dramatic function" in the narrative
        """
```

```python
class AgentSeed(BaseModel):
    name: str
    agent_type: str          # From AgentType enum
    role: str                # "CEO of Prometheus Labs"
    entity_name: str         # Links to entity
    faction: str             # Links to faction
    dramatic_function: str   # "protagonist", "antagonist", "wildcard", "catalyst"
    
    # Personality — NOT random defaults, but CRAFTED for tension
    personality: PersonalitySeed
    
    # Backstory — feeds into initial memories
    backstory: str           # "Former Google researcher who left to build safe AGI..."
    secret: str              # "Secretly funded by Chinese military"
    
    # Starting position
    initial_resources: Dict  # {"funding": 0.8, "talent": 0.7, "compute": 0.9}
    initial_reputation: float
```

```python
class PersonalitySeed(BaseModel):
    """Personality crafted for dramatic tension, not random."""
    
    # Big Five
    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float
    
    # Simulation traits
    risk_tolerance: float
    ambition: float
    empathy: float
    rationality: float
    creativity: float
    morality: float
    
    # WHY these values — the LLM explains its casting choices
    personality_rationale: str  # "High risk + low morality creates a 'move fast, break things' archetype"
```

> [!IMPORTANT]
> **Key Innovation**: The `dramatic_function` field ensures the LLM doesn't just generate random agents. Every agent serves a narrative purpose — protagonist, antagonist, wildcard, or catalyst. This creates natural story arcs.

---

### Pass 4 — Goal & Knowledge Weaving (`goal_weaver.py`)

Assigns goals and seeds the **hidden knowledge layer** for each agent:

```python
class GoalWeaver:
    async def weave(
        self,
        dna: ScenarioDNA,
        agents: List[AgentSeed],
        entities: List[EntitySeed],
    ) -> Tuple[List[GoalSeed], List[HiddenFactSeed]]:
        """
        For each agent:
        1. Generate 1-3 goals that align with their faction/dramatic function
        2. Generate hidden facts that are discoverable during intel phase
        
        Goals should CONFLICT — CEO A's goal should threaten CEO B's.
        Hidden facts should be ACTIONABLE — discovering them enables new actions.
        """
```

```python
class GoalSeed(BaseModel):
    agent_name: str          # Links to agent
    description: str         # "Achieve AGI before Prometheus Labs"
    goal_type: str           # GoalType enum value
    priority: float          # 0-1
    conflicts_with: List[str]  # Other agent names whose goals this opposes

class HiddenFactSeed(BaseModel):
    """A discoverable fact seeded into the world knowledge system."""
    fact: str                    # "Prometheus Labs' safety team has been systematically silenced"
    discoverable_by: List[str]   # Agent types or "*" for anyone
    discovery_context: str       # "investigation", "whistleblower", "leaked_document"
    goal_relevance: str          # Which goal type this is relevant to
    action_it_enables: str       # "expose_prometheus_safety_coverup"
```

> [!TIP]
> **Hidden facts are the fuel of the simulation.** When an agent gathers information, they discover these facts, which unlock new candidate actions. By seeding scenario-specific hidden facts, the simulation produces actions that are **thematically relevant** to the user's "what if" prompt instead of generic corporate espionage.

---

### Pass 5 — Tension Wiring (`tension_wirer.py`)

The final pass wires up **agent-to-agent relationships** based on faction dynamics:

```python
class TensionWirer:
    async def wire(
        self,
        dna: ScenarioDNA,
        agents: List[AgentSeed],
    ) -> List[RelationshipSeed]:
        """
        Wire up starting relationships based on:
        1. Same faction = positive relationship (ally/friend)
        2. Opposing faction = negative relationship (rival/enemy)
        3. Wildcards = neutral with everyone (they're unpredictable)
        4. Core tension alignment — agents on opposite sides get rivalry
        """
```

```python
class RelationshipSeed(BaseModel):
    agent_a_name: str
    agent_b_name: str
    relationship_type: str   # "rival", "ally", "neutral", "mentor", etc.
    strength: float          # -1 to 1
    trust: float             # 0 to 1
    tension_source: str      # "competing for AGI dominance"
```

---

## API Design

### Primary Endpoint: One-Shot World Generation

```
POST /api/seed/generate
```

**Request**:
```json
{
  "prompt": "What if AGI is achieved by 2029?",
  "settings": {
    "agent_count": null,          // null = let LLM decide (3-8)
    "intensity": null,            // null = let LLM decide (0-1)
    "recommended_steps": null,    // null = let LLM decide
    "include_wildcards": true,    // Add unpredictable agents
    "theme_focus": null           // null = balanced, or "political", "economic", "social"
  }
}
```

**Response** (full seed payload — returned BEFORE database writes):
```json
{
  "seed_id": "uuid",
  "dna": { ... },
  "world_state": { ... },
  "entities": [ ... ],
  "agents": [ ... ],
  "goals": [ ... ],
  "hidden_facts": [ ... ],
  "relationships": [ ... ],
  "estimated_tokens_used": 12500,
  "generation_time_ms": 4200
}
```

> [!NOTE]
> The seed is returned as a **preview** before committing. This lets the user inspect, remix, and approve before the simulation world is created.

---

### Remix Endpoint: Modify Before Committing

```
PUT /api/seed/{seed_id}/remix
```

**Request** — partial overrides for any part of the seed:
```json
{
  "agents": {
    "add": [{ "name": "Elon Musk", "agent_type": "ceo", ... }],
    "remove": ["Agent Name"],
    "modify": {
      "Dr. Sarah Chen": {
        "personality": { "risk_tolerance": 0.9 },
        "role": "CTO of DeepMind"
      }
    }
  },
  "world_state": {
    "regulatory_pressure": { "ai_industry": 0.8 }
  },
  "goals": {
    "add": [{ "agent_name": "Elon Musk", "description": "Open-source AGI", ... }]
  }
}
```

---

### Commit Endpoint: Create Everything

```
POST /api/seed/{seed_id}/commit
```

This creates the project, world state, entities, agents, goals, relationships — all in one transactional operation. Returns the `project_id` ready for simulation.

**Response**:
```json
{
  "project_id": "uuid",
  "project_name": "The AGI Race",
  "agents_created": 5,
  "entities_created": 4,
  "goals_created": 12,
  "relationships_created": 8,
  "hidden_facts_seeded": 15,
  "ready_to_simulate": true,
  "suggested_steps": 12,
  "message": "World generated. Run POST /api/projects/{id}/simulate/step to begin."
}
```

---

### Quick-Launch Endpoint: Generate + Commit in One

For users who don't want to preview:

```
POST /api/seed/quick-launch
```

**Request**:
```json
{
  "prompt": "Cold War but with AI superpowers instead of nukes",
  "auto_simulate": true,
  "max_steps": 10,
  "step_delay_seconds": 2
}
```

Generates the world AND starts the simulation automatically.

---

## Hidden Knowledge Seeding

This is the most innovative part. Today, `world_knowledge.py` has a **static** dictionary of hidden facts (`HIDDEN_FACTS`). The Seeder will add a dynamic layer:

```python
# In world_knowledge.py — new method

class WorldKnowledgeSystem:
    def register_scenario_facts(
        self,
        project_id: UUID,
        facts: List[HiddenFactSeed],
    ):
        """
        Register scenario-specific hidden facts.
        
        These are stored per-project and merged with the
        static HIDDEN_FACTS during gather_information().
        
        This is how "What if AGI by 2029?" produces discoveries like:
        - "Prometheus Labs' safety team has been silenced"
        instead of generic:
        - "A key player in this space is more vulnerable than they appear"
        """
```

**Storage**: A new `scenario_facts` table, or stored in the `WorldState.state` JSONB field under a `hidden_facts` key.

---

## User Override Philosophy

The system follows a **"sane defaults, full control"** philosophy:

| Layer | Default | Override |
|-------|---------|----------|
| Agent count | LLM decides (3-8) | User specifies exact count |
| Personalities | LLM crafts for drama | User modifies any trait |
| Goals | LLM generates from DNA | User adds/removes/changes |
| World state | LLM generates from themes | User merges custom values |
| Hidden facts | LLM generates scenario-specific | User adds custom facts |
| Entities | LLM generates from factions | User adds real-world entities |

---

## Token Budget & Cost Estimation

Each generation pass uses ~1000-2000 tokens. Full pipeline:

| Pass | Estimated Tokens | Description |
|------|-----------------|-------------|
| DNA Extraction | ~1500 | Extract scenario structure |
| World Fabric | ~800 | Generate world conditions |
| Entity Graph | ~1200 | Generate entities + relationships |
| Agent Casting | ~2000 | Cast agents with personalities |
| Goal Weaving | ~1500 | Assign goals + hidden facts |
| Tension Wiring | ~800 | Wire relationships |
| **Total** | **~7800** | **~$0.002 on Groq** |

This is cheap enough to run on every prompt without concern.

---

## Implementation Order

1. **`seed_models.py`** — Define all Pydantic models (ScenarioDNA, FactionBlueprint, AgentSeed, etc.)
2. **`dna_extractor.py`** — Pass 0 (standalone, testable)
3. **`world_fabricator.py`** — Pass 1
4. **`entity_generator.py`** — Pass 2
5. **`agent_caster.py`** — Pass 3
6. **`goal_weaver.py`** — Pass 4 + hidden fact registration
7. **`tension_wirer.py`** — Pass 5
8. **`scenario_seeder.py`** — Orchestrator that chains all passes
9. **`api/seeder.py`** — API endpoints
10. **`world_knowledge.py`** — Add dynamic fact registration

---

## Success Criteria

- [ ] `POST /api/seed/generate` with prompt "What if AGI by 2029?" returns a complete seed in < 10 seconds
- [ ] Generated agents have **conflicting goals** (not all doing the same thing)
- [ ] Generated personalities create **natural friction** (not all 0.5 defaults)
- [ ] Hidden facts are **scenario-specific** (not generic placeholders)
- [ ] `POST /api/seed/{id}/commit` creates a fully runnable simulation world
- [ ] Running the simulation produces **thematically relevant** actions and discoveries
- [ ] User can remix any part of the seed before committing
