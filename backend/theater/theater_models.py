from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class TensionPhase(str, Enum):
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    LULL = "lull"

class TensionMetrics(BaseModel):
    """Real-time dramatic tension measurement for a step."""
    step: int
    overall_tension: float = Field(..., ge=0.0, le=1.0)
    
    # Component scores
    conflict_intensity: float = Field(..., ge=0.0, le=1.0)
    stakes_level: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    momentum_shift: float = Field(..., ge=0.0, le=1.0)
    relationship_volatility: float = Field(..., ge=0.0, le=1.0)
    
    # Narrative markers
    is_climax_candidate: bool
    is_lull: bool
    phase: TensionPhase
    
    # Sources of tension
    tension_sources: List[str]

class PacingMode(str, Enum):
    MANUAL = "manual"
    AUTO_UNIFORM = "uniform"
    AUTO_DRAMATIC = "dramatic"

class PacingRecommendation(BaseModel):
    """Recommendation for how long to delay before the next step."""
    delay_seconds: float
    should_pause: bool
    reason: str

class DivergenceBranch(BaseModel):
    """A possible alternative path branching from a divergence point."""
    label: str
    description: str
    modifications: Dict[str, Any]
    estimated_impact: str

class DivergencePoint(BaseModel):
    """A critical juncture where the timeline could branch."""
    step: int
    description: str
    significance: float = Field(..., ge=0.0, le=1.0)
    branches: List[DivergenceBranch]
    
    # State snapshot for branch recreation
    world_state_snapshot: Dict[str, Any]
    agent_states_snapshot: Dict[str, Any]

class InjectedEvent(BaseModel):
    """An external event injected into the simulation."""
    description: str
    event_type: str
    
    # Effects
    world_state_changes: Optional[Dict[str, Any]] = None
    affected_agents: Optional[List[str]] = None
    visibility: float = Field(1.0, ge=0.0, le=1.0)
    
    # Narrative
    source: str = "user_injection"

class InjectionResult(BaseModel):
    """Result of injecting an event."""
    success: bool
    message: str
    event: InjectedEvent

class AgentBeat(BaseModel):
    """Narrative beat for a specific agent."""
    agent_name: str
    action_summary: str
    motivation_insight: str
    emotional_state: str

class StepNarrative(BaseModel):
    """Story prose generated for a single step."""
    step: int
    phase: str
    headline: str
    summary: str
    
    agent_beats: List[AgentBeat]
    open_questions: List[str]
    foreshadowing: Optional[str] = None

class CharacterArc(BaseModel):
    """Analysis of how an agent evolved."""
    agent_name: str
    role: str
    starting_position: str
    ending_position: str
    key_moments: List[str]
    arc_type: str

class SimulationStory(BaseModel):
    """Compiled narrative of the entire simulation."""
    title: str
    prologue: str
    chapters: List[StepNarrative]
    epilogue: str
    
    character_arcs: List[CharacterArc]
    themes_explored: List[str]
    key_insights: List[str]
    
    tension_arc: List[float]
    total_actions: int
    total_patterns: int
    timelines_explored: int
