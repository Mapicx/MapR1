"""
MapR1 — Seed Models

Pydantic models for the scenario seeder pipeline.
These represent the intermediate and final outputs of each generation pass.
"""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


# ── Pass 0: DNA Extraction ──────────────────────────────────────────────────


class FactionBlueprint(BaseModel):
    """Blueprint for a faction in the scenario."""
    name: str = Field(..., description="Faction name (e.g., 'The Builders')")
    archetype: str = Field(..., description="Faction archetype (e.g., 'technology_company')")
    motivation: str = Field(..., description="Core motivation")
    stance_on_core_tension: str = Field(..., description="Position on the main conflict")
    key_resource: str = Field(..., description="What they control")
    vulnerability: str = Field(..., description="Their weakness")


class ScenarioDNA(BaseModel):
    """The genetic code of a scenario — everything needed to build a world."""
    
    # Core identity
    title: str = Field(..., description="Scenario title")
    premise: str = Field(..., description="1-paragraph scenario description")
    time_horizon: Tuple[int, int] = Field(..., description="(start_year, end_year)")
    
    # Thematic structure
    primary_themes: List[str] = Field(..., description="Main themes")
    core_tension: str = Field(..., description="Central conflict")
    secondary_tensions: List[str] = Field(default_factory=list, description="Additional conflicts")
    
    # Faction blueprint
    factions: List[FactionBlueprint] = Field(..., description="Faction blueprints")
    
    # World conditions
    starting_conditions: Dict[str, str] = Field(default_factory=dict, description="Initial world state")
    key_variables: List[str] = Field(default_factory=list, description="Important variables to track")
    
    # Narrative seeds
    inciting_incidents: List[str] = Field(default_factory=list, description="Events that kick off the scenario")
    potential_wildcards: List[str] = Field(default_factory=list, description="Unpredictable events")
    
    # Complexity settings
    recommended_agent_count: int = Field(..., ge=3, le=8, description="Ideal agent count")
    recommended_step_count: int = Field(..., ge=6, le=20, description="Ideal simulation steps")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Scenario volatility")


# ── Pass 1: World Fabric ────────────────────────────────────────────────────


class WorldFabric(BaseModel):
    """Initial world state conditions."""
    market_conditions: Dict[str, float] = Field(default_factory=dict)
    public_opinion: Dict[str, float] = Field(default_factory=dict)
    media_attention: Dict[str, float] = Field(default_factory=dict)
    regulatory_pressure: Dict[str, float] = Field(default_factory=dict)


# ── Pass 2: Entity Generation ───────────────────────────────────────────────


class EntitySeed(BaseModel):
    """Seed for creating an entity."""
    name: str
    type: str = Field(..., description="Entity type from theme institution keys (e.g. institution_0)")
    faction: str = Field(..., description="Which faction blueprint it belongs to")
    description: str
    attributes: Dict = Field(default_factory=dict, description="Sector, size, influence, etc.")


class EntityRelationshipSeed(BaseModel):
    """Seed for entity-to-entity relationship."""
    entity_a: str
    entity_b: str
    relationship_type: str = Field(..., description="rival, alliance, trade_partner, etc.")
    strength: str = Field(..., description="weak, medium, strong")
    description: str


# ── Pass 3: Agent Casting ───────────────────────────────────────────────────


class PersonalitySeed(BaseModel):
    """Personality crafted for dramatic tension."""
    
    # Big Five
    openness: float = Field(..., ge=0.0, le=1.0)
    conscientiousness: float = Field(..., ge=0.0, le=1.0)
    extraversion: float = Field(..., ge=0.0, le=1.0)
    agreeableness: float = Field(..., ge=0.0, le=1.0)
    neuroticism: float = Field(..., ge=0.0, le=1.0)
    
    # Simulation traits
    risk_tolerance: float = Field(..., ge=0.0, le=1.0)
    ambition: float = Field(..., ge=0.0, le=1.0)
    empathy: float = Field(..., ge=0.0, le=1.0)
    rationality: float = Field(..., ge=0.0, le=1.0)
    creativity: float = Field(..., ge=0.0, le=1.0)
    morality: float = Field(..., ge=0.0, le=1.0)
    
    # Rationale
    personality_rationale: str = Field(..., description="Why these values create drama")


class AgentSeed(BaseModel):
    """Seed for creating an agent."""
    name: str
    agent_type: str = Field(..., description="Agent type from theme role keys (e.g. role_0)")
    role: str = Field(..., description="Specific title or position")
    entity_name: str = Field(..., description="Links to entity")
    faction: str = Field(..., description="Links to faction")
    dramatic_function: str = Field(..., description="protagonist, antagonist, wildcard, catalyst")
    
    # Personality
    personality: PersonalitySeed
    
    # Backstory
    backstory: str = Field(..., description="Character background")
    secret: str = Field(..., description="Hidden information")
    
    # Starting position
    initial_resources: Dict[str, float] = Field(default_factory=dict)
    initial_reputation: float = Field(default=0.5, ge=0.0, le=1.0)


# ── Pass 4: Goal & Knowledge Weaving ────────────────────────────────────────


class GoalSeed(BaseModel):
    """Seed for creating an agent goal."""
    agent_name: str
    description: str
    goal_type: str = Field(..., description="Goal type from theme victory/failure keys (e.g. victory_0)")
    priority: float = Field(..., ge=0.0, le=1.0)
    conflicts_with: List[str] = Field(default_factory=list, description="Other agent names")


class HiddenFactSeed(BaseModel):
    """A discoverable fact seeded into the world knowledge system."""
    fact: str
    discoverable_by: List[str] = Field(..., description="Agent types or '*' for anyone")
    discovery_context: str = Field(..., description="investigation, whistleblower, etc.")
    goal_relevance: str = Field(..., description="Which goal type this is relevant to")
    action_it_enables: str = Field(..., description="What action this unlocks")


# ── Pass 5: Tension Wiring ──────────────────────────────────────────────────


class RelationshipSeed(BaseModel):
    """Seed for agent-to-agent relationship."""
    agent_a_name: str
    agent_b_name: str
    relationship_type: str = Field(..., description="rival, ally, neutral, mentor, etc.")
    strength: float = Field(..., ge=-1.0, le=1.0)
    trust: float = Field(..., ge=0.0, le=1.0)
    tension_source: str = Field(..., description="Why this relationship exists")


# ── Complete Seed Package ───────────────────────────────────────────────────


class CompleteSeed(BaseModel):
    """Complete seed package ready for commit."""
    seed_id: UUID = Field(default_factory=uuid4)
    
    # All generation outputs
    dna: ScenarioDNA
    world_fabric: WorldFabric
    entities: List[EntitySeed]
    entity_relationships: List[EntityRelationshipSeed]
    agents: List[AgentSeed]
    goals: List[GoalSeed]
    hidden_facts: List[HiddenFactSeed]
    relationships: List[RelationshipSeed]
    
    # Metadata
    estimated_tokens_used: int = 0
    generation_time_ms: int = 0
    compiled_theme: Dict = Field(default_factory=dict, description="Dump of the CompiledTheme used")


# ── API Request/Response Models ─────────────────────────────────────────────


class GenerateRequest(BaseModel):
    """Request to generate a scenario seed."""
    prompt: str = Field(..., min_length=10, description="User's 'what if' prompt")
    settings: Optional[Dict] = Field(default_factory=dict, description="Optional overrides")


class RemixRequest(BaseModel):
    """Request to remix parts of a seed."""
    agents: Optional[Dict] = None
    world_state: Optional[Dict] = None
    goals: Optional[Dict] = None
    entities: Optional[Dict] = None


class CommitResponse(BaseModel):
    """Response after committing a seed to the database."""
    project_id: UUID
    project_name: str
    agents_created: int
    entities_created: int
    goals_created: int
    relationships_created: int
    hidden_facts_seeded: int
    ready_to_simulate: bool
    suggested_steps: int
    message: str


class QuickLaunchRequest(BaseModel):
    """Request for quick-launch (generate + commit + simulate)."""
    prompt: str = Field(..., min_length=10)
    auto_simulate: bool = True
    max_steps: int = Field(default=10, ge=1, le=50)
    step_delay_seconds: float = Field(default=2.0, ge=0.0, le=10.0)
