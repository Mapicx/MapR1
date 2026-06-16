"""
Agent models for autonomous decision-making entities.

Agents are the "brains" that make decisions. They can be linked to entities
(e.g., CEO agent for a company entity) or exist independently (e.g., pure AI agent).
"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

from backend.models.db_models import Base


class Agent(Base):
    """
    Autonomous agent that makes decisions.
    
    An agent is the "brain" that makes decisions. It can be:
    - Linked to an entity (CEO agent for a company)
    - Independent (pure AI agent, autonomous system)
    
    One entity can have multiple agents (company has CEO, CFO, CTO).
    """
    __tablename__ = "agents"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True)
    
    # Identity
    name = Column(String(255), nullable=False)
    agent_type = Column(String(50), nullable=False)  # From AgentType enum
    role = Column(String(255), nullable=False)  # "CEO of TechCorp", "President of Nation X"
    status = Column(String(50), nullable=False, default="active")  # "active" or "collapsed"
    
    # State (JSONB for flexibility)
    personality = Column(JSONB, nullable=False, default=dict)  # Personality traits
    mutable_psychology = Column(JSONB, nullable=False, default=dict) # Mutable psychology
    current_state = Column(JSONB, nullable=False, default=dict)  # Current emotional/mental state
    resources = Column(JSONB, nullable=False, default=dict)  # Available resources
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="agents")
    entity = relationship("Entity", back_populates="agents")
    memories = relationship("AgentMemory", back_populates="agent", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="agent", cascade="all, delete-orphan")


class AgentMemory(Base):
    """
    Agent's memory of events, interactions, and decisions.
    
    Memories are stored in both:
    - Database (structured data, relationships)
    - ChromaDB (semantic search)
    """
    __tablename__ = "agent_memories"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Memory content
    memory_type = Column(String(50), nullable=False)  # observation, interaction, decision, emotion
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False, default=0.5)  # 0-1 (how important is this memory)
    emotional_valence = Column(Float, nullable=False, default=0.0)  # -1 to 1 (negative to positive)
    
    # Context
    related_agent_ids = Column(ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list)
    related_entity_ids = Column(ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list)
    world_state_snapshot = Column(JSONB, nullable=False, default=dict)  # World state at time of memory
    
    # Metadata
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="memories")


# ============================================================================
# Pydantic Models for API
# ============================================================================

class AgentType(str, Enum):
    """All available agent types across 10 categories"""
    
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


class MemoryType(str, Enum):
    """Types of memories agents can have"""
    OBSERVATION = "observation"  # Observed an event
    INTERACTION = "interaction"  # Interacted with another agent/entity
    DECISION = "decision"  # Made a decision
    EMOTION = "emotion"  # Emotional response


class Personality(BaseModel):
    """
    Agent personality traits.
    
    Based on Big Five personality model + additional traits
    for simulation realism.
    """
    
    # Big Five personality traits
    openness: float = Field(default=0.5, ge=0.0, le=1.0, description="Conservative to open")
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0, description="Spontaneous to organized")
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0, description="Introverted to extraverted")
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0, description="Competitive to cooperative")
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0, description="Stable to anxious")
    
    # Additional traits for simulation
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0, description="Risk-averse to risk-seeking")
    ambition: float = Field(default=0.5, ge=0.0, le=1.0, description="Content to ambitious")
    empathy: float = Field(default=0.5, ge=0.0, le=1.0, description="Cold to empathetic")
    rationality: float = Field(default=0.5, ge=0.0, le=1.0, description="Emotional to rational")
    creativity: float = Field(default=0.5, ge=0.0, le=1.0, description="Conventional to creative")
    morality: float = Field(default=0.5, ge=0.0, le=1.0, description="Pragmatic to principled")

class MutablePsychology(BaseModel):
    """
    Evolving psychological traits that shift based on game events.
    """
    greed: float = Field(default=0.5, ge=0.0, le=1.0)
    fear: float = Field(default=0.2, ge=0.0, le=1.0)
    ego: float = Field(default=0.5, ge=0.0, le=1.0)
    paranoia: float = Field(default=0.3, ge=0.0, le=1.0)
    idealism: float = Field(default=0.5, ge=0.0, le=1.0)
    radicalization: float = Field(default=0.1, ge=0.0, le=1.0)
    nihilism: float = Field(default=0.0, ge=0.0, le=1.0)
    desperation: float = Field(default=0.0, ge=0.0, le=1.0)
    betrayal_wounds: int = Field(default=0, ge=0)
    consecutive_failures: int = Field(default=0, ge=0)
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)

class AgentCreate(BaseModel):
    """Request to create an agent"""
    name: str = Field(..., min_length=1, max_length=255)
    agent_type: AgentType
    role: str = Field(..., min_length=1, max_length=255)
    personality: Personality = Field(default_factory=Personality)
    mutable_psychology: Dict = Field(default_factory=dict)
    entity_id: Optional[UUID] = None
    current_state: Dict = Field(default_factory=dict)
    resources: Dict = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Request to update an agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    personality: Optional[Personality] = None
    mutable_psychology: Optional[Dict] = None
    current_state: Optional[Dict] = None
    resources: Optional[Dict] = None


class AgentResponse(BaseModel):
    """Agent response"""
    id: UUID
    project_id: UUID
    entity_id: Optional[UUID]
    name: str
    agent_type: str
    role: str
    status: str = "active"
    personality: Dict
    mutable_psychology: Dict
    current_state: Dict
    resources: Dict
    created_at: datetime
    last_active: datetime
    
    class Config:
        from_attributes = True


class MemoryCreate(BaseModel):
    """Request to create a memory"""
    memory_type: MemoryType
    content: str = Field(..., min_length=1)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotional_valence: float = Field(default=0.0, ge=-1.0, le=1.0)
    related_agent_ids: List[UUID] = Field(default_factory=list)
    related_entity_ids: List[UUID] = Field(default_factory=list)
    world_state_snapshot: Dict = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None


class MemoryResponse(BaseModel):
    """Memory response"""
    id: UUID
    agent_id: UUID
    memory_type: str
    content: str
    importance: float
    emotional_valence: float
    related_agent_ids: List[UUID]
    related_entity_ids: List[UUID]
    world_state_snapshot: Dict
    occurred_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class MemoryRecallRequest(BaseModel):
    """Request to recall memories semantically"""
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ContextBuildRequest(BaseModel):
    """Request to build decision context"""
    situation: str = Field(..., min_length=1)
    include_recent: int = Field(default=5, ge=1, le=20)
    include_important: int = Field(default=5, ge=1, le=20)
    include_similar: int = Field(default=5, ge=1, le=20)


# ============================================================================
# Agent Type Categories
# ============================================================================

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


# ============================================================================
# Default Personalities by Agent Type
# ============================================================================

DEFAULT_PERSONALITIES = {
    # Business
    "ceo": Personality(ambition=0.9, risk_tolerance=0.7, rationality=0.8, empathy=0.5, morality=0.6),
    "cfo": Personality(conscientiousness=0.9, rationality=0.9, risk_tolerance=0.3, ambition=0.7),
    "cto": Personality(creativity=0.8, rationality=0.8, openness=0.9, conscientiousness=0.7),
    
    # Government
    "policy": Personality(rationality=0.8, conscientiousness=0.8, empathy=0.6, morality=0.7),
    "diplomacy": Personality(agreeableness=0.8, empathy=0.7, rationality=0.7, extraversion=0.7),
    
    # Social
    "activist": Personality(ambition=0.7, empathy=0.9, morality=0.9, rationality=0.5, risk_tolerance=0.6),
    "religious_leader": Personality(empathy=0.8, morality=0.9, agreeableness=0.7, extraversion=0.6),
    
    # Criminal
    "hacker": Personality(creativity=0.9, risk_tolerance=0.8, rationality=0.7, morality=0.3, empathy=0.4),
    "smuggler": Personality(risk_tolerance=0.9, morality=0.2, rationality=0.6, ambition=0.7),
    
    # Military
    "spy": Personality(rationality=0.9, empathy=0.2, risk_tolerance=0.8, morality=0.4, conscientiousness=0.8),
    "commander": Personality(conscientiousness=0.9, rationality=0.8, ambition=0.7, agreeableness=0.4),
    
    # Healthcare
    "doctor": Personality(empathy=0.9, conscientiousness=0.9, morality=0.8, rationality=0.7, risk_tolerance=0.3),
    "surgeon": Personality(conscientiousness=0.95, rationality=0.9, risk_tolerance=0.4, empathy=0.7),
    
    # Creative
    "artist": Personality(creativity=0.9, openness=0.9, rationality=0.3, empathy=0.7, risk_tolerance=0.6),
    "writer": Personality(creativity=0.8, openness=0.8, empathy=0.7, rationality=0.5),
}


def get_default_personality(agent_type: str) -> Personality:
    """Get default personality for an agent type"""
    return DEFAULT_PERSONALITIES.get(agent_type, Personality())
