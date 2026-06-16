"""
Action models for agent decisions and simulation.

Tracks agent actions, decisions, and their outcomes.
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

from backend.models.db_models import Base


class AgentAction(Base):
    """
    Record of an agent's action in the simulation.
    
    Tracks what the agent decided to do and the outcome.
    """
    __tablename__ = "agent_actions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    simulation_step = Column(Integer, nullable=False)
    
    # Action details
    action_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Execution
    executed = Column(Boolean, nullable=False, default=False)
    success = Column(Boolean, nullable=True)
    outcome = Column(Text, nullable=True)
    impact = Column(JSONB, nullable=False, default=dict)  # What changed
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent")
    project = relationship("Project")


class SimulationState(Base):
    """
    Tracks simulation progress for a project.
    """
    __tablename__ = "simulation_states"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # State
    current_step = Column(Integer, nullable=False, default=0)
    is_running = Column(Boolean, nullable=False, default=False)
    total_actions = Column(Integer, nullable=False, default=0)
    
    # Metadata
    started_at = Column(DateTime, nullable=True)
    last_step_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project")


class EmergentPattern(Base):
    """
    Detected emergent pattern in simulation.
    """
    __tablename__ = "emergent_patterns"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Pattern details
    pattern_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    significance = Column(Float, nullable=False)  # 0-1
    
    # Context
    involved_agent_ids = Column(JSONB, nullable=False, default=list)
    involved_entity_ids = Column(JSONB, nullable=False, default=list)
    evidence = Column(JSONB, nullable=False, default=list)  # Supporting events/actions
    
    # Timeline
    first_detected_step = Column(Integer, nullable=False)
    last_updated_step = Column(Integer, nullable=False)
    
    # Metadata
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project")


# ============================================================================
# Pydantic Models for API
# ============================================================================

class ActionType(str, Enum):
    """Types of actions agents can take"""
    # Economic
    EXPAND_BUSINESS = "expand_business"
    LAUNCH_PRODUCT = "launch_product"
    ACQUIRE_COMPANY = "acquire_company"
    INVEST = "invest"
    TRADE = "trade"
    BID_ON_CONTRACT = "bid_on_contract"
    HOSTILE_TAKEOVER = "hostile_takeover"
    POACH_TALENT = "poach_talent"
    
    # Political
    PROPOSE_POLICY = "propose_policy"
    FORM_ALLIANCE = "form_alliance"
    DECLARE_WAR = "declare_war"
    NEGOTIATE = "negotiate"
    IMPOSE_SANCTIONS = "impose_sanctions"
    LOBBY_INFLUENCERS = "lobby_influencers"
    FILE_LEGAL_ACTION = "file_legal_action"
    
    # Social
    BUILD_RELATIONSHIP = "build_relationship"
    SPREAD_IDEOLOGY = "spread_ideology"
    ORGANIZE_MOVEMENT = "organize_movement"
    HELP_OTHERS = "help_others"
    MEDIA_CAMPAIGN = "media_campaign"
    
    # Aggressive
    ATTACK = "attack"
    SABOTAGE = "sabotage"
    BETRAY = "betray"
    SEEK_REVENGE = "seek_revenge"
    EXPLOIT_VULNERABILITY = "exploit_vulnerability"
    LEAK_SECRETS = "leak_secrets"
    
    # Defensive
    FORTIFY = "fortify"
    BUILD_DEFENSES = "build_defenses"
    DEFENSIVE_RESTRUCTURING = "defensive_restructuring"
    
    # Neutral
    RESEARCH = "research"
    INNOVATE = "innovate"
    WAIT = "wait"
    
    # Intel
    GATHER_INTEL = "gather_intel"


class IntelShareDecision(BaseModel):
    """LLM decision for sharing intel with an ally."""
    target_agent_id: str = Field(..., description="The ID of the ally to share with.")
    fact_content: str = Field(..., description="The content of the fact to share.")
    is_fabricated: bool = Field(..., description="Whether the fact is intentionally fabricated/false.")
    distortion_intent: Literal["none", "inflate", "deflate", "mislead"] = Field(
        ..., description="The intent behind the distortion."
    )
    reasoning: str = Field(
        ..., description="Internal reasoning for this share. LOG-ONLY. Never shown to receiver."
    )


class AgentDecision(BaseModel):
    """Structured decision output from LLM"""
    action: ActionType = Field(..., description="The chosen action")
    reasoning: str = Field(..., description="Why this action was chosen")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in decision (0-1)")
    expected_outcome: str = Field(..., description="What the agent expects to happen")
    risks: List[str] = Field(default_factory=list, description="Potential risks identified")
    affected_agents: List[str] = Field(default_factory=list, description="Other agents this might affect")
    proposal_responses: Dict[str, str] = Field(default_factory=dict, description="Dictionary mapping Proposal ID to 'accept' or 'reject'.")
    outgoing_proposals: List[Dict[str, str]] = Field(default_factory=list, description="List of proposals to send to other agents. Format: [{'target_name': '...', 'type': 'alliance', 'context': 'Why you want this'}]. Leave empty if none.")
    intel_shares: List[IntelShareDecision] = Field(..., description="REQUIRED. List of intel sharing decisions to your allies. Return an empty list [] if you have no intel to share or no allies.")


class ActionExecutionResult(BaseModel):
    """Result of executing an action"""
    success: bool
    outcome: str
    impact: Dict[str, Any] = Field(default_factory=dict)
    side_effects: List[str] = Field(default_factory=list)
    affected_agents: List[UUID] = Field(default_factory=list)
    world_state_changes: Dict[str, Any] = Field(default_factory=dict)
    public_impact: bool = True


class ActionResponse(BaseModel):
    """Action response"""
    id: UUID
    agent_id: UUID
    agent_name: str
    action_type: str
    description: str
    reasoning: str
    confidence: float
    executed: bool
    success: Optional[bool]
    outcome: Optional[str]
    impact: Dict
    public_impact: bool = True
    simulation_step: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SimulationStepResult(BaseModel):
    """Result of one simulation step"""
    step_number: int
    actions: List[ActionResponse]
    events_generated: int
    patterns_detected: int
    world_state_changes: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    success: bool = Field(default=True, description="Whether the step completed successfully")
    error: Optional[str] = Field(default=None, description="Error code if step failed")

class DiaryEntry(BaseModel):
    """Raw agent diary entry tracking per-step reasoning and state of mind."""
    agent_id: str
    agent_name: str
    step_number: int
    action_taken: str
    action_succeeded: bool
    reasoning: str
    psychology_snapshot: dict
    allies_at_time: List[str]

class PatternType(str, Enum):
    """Types of emergent patterns"""
    ALLIANCE_FORMATION = "alliance_formation"
    CONFLICT_ESCALATION = "conflict_escalation"
    ECONOMIC_TREND = "economic_trend"
    SOCIAL_MOVEMENT = "social_movement"
    POWER_SHIFT = "power_shift"
    CULTURAL_CHANGE = "cultural_change"
    ARMS_RACE = "arms_race"
    TRADE_NETWORK = "trade_network"
    IDEOLOGY_SPREAD = "ideology_spread"
    REVOLUTION = "revolution"


class PatternResponse(BaseModel):
    """Emergent pattern response"""
    id: UUID
    project_id: UUID
    pattern_type: str
    title: str
    description: str
    significance: float
    involved_agent_ids: List
    involved_entity_ids: List
    evidence: List
    first_detected_step: int
    last_updated_step: int
    detected_at: datetime
    
    class Config:
        from_attributes = True


class PatternDetectionRequest(BaseModel):
    """Request to detect patterns"""
    time_window: int = Field(default=10, ge=1, le=100, description="Number of recent steps to analyze")
    min_significance: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum significance threshold")


class SimulationControlRequest(BaseModel):
    """Request to control simulation"""
    max_steps: Optional[int] = Field(None, ge=1, le=1000)
    step_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Delay between steps in seconds")


# ============================================================================
# Decision Pipeline Phase 1 Models
# ============================================================================

class CandidateAction(BaseModel):
    """A context-aware candidate action generated from discoveries."""
    action_name: str = Field(..., description="Internal action name, e.g. 'exploit_rivalcorp_supply_chain_weakness'")
    display_name: str = Field(..., description="Human-readable action name for LLM, e.g. 'Exploit RivalCorp supply chain weakness'")
    source_fact: str = Field(..., description="The discovery that generated this action")
    goal_alignment: float = Field(..., ge=0.0, le=1.0, description="How well it aligns with primary goal (0-1)")
    risk_level: float = Field(..., ge=0.0, le=1.0, description="Estimated risk (0-1)")
    cooldown_penalty: float = Field(default=0.0, ge=0.0, le=1.0, description="Penalty from recent attempts (0 = no penalty)")


class RecentAction(BaseModel):
    """Recent action for cooldown tracking"""
    action_type: str = Field(..., description="The action type that was attempted")
    action_category: str = Field(..., description="Category mapped from action_type")
    step_number: int = Field(..., description="Simulation step when action was taken")
    success: bool = Field(..., description="Whether the action succeeded")
    outcome: str = Field(..., description="Outcome description")
