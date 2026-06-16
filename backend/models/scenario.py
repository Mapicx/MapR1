"""
MapR1 — Scenario Data Models
Defines the structure for scenarios, timelines, and events.
"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ScenarioCategory(str, Enum):
    """Category of scenario outcome"""
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class TimelineEvent(BaseModel):
    """A single event in a timeline"""
    year: int = Field(..., description="Year when event occurs")
    description: str = Field(..., description="What happens")
    impact: str = Field(default="medium", description="Impact level: low, medium, high")


class Scenario(BaseModel):
    """A single future scenario"""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique scenario ID")
    title: str = Field(..., description="Short title for the scenario")
    description: str = Field(..., description="2-3 sentence description")
    category: ScenarioCategory = Field(..., description="Scenario category")
    probability: float = Field(default=0.33, ge=0.0, le=1.0, description="Estimated probability")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Chronological events")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScenarioRequest(BaseModel):
    """Request to generate scenarios"""
    prompt: str = Field(..., min_length=10, max_length=500, description="User's scenario prompt")
    num_scenarios: int = Field(default=3, ge=1, le=5, description="Number of scenarios to generate")


class ScenarioResponse(BaseModel):
    """Response containing generated scenarios"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    scenarios: List[Scenario]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = Field(default="qwen3.5:4b")


# Structured output models for LLM generation
class LLMTimelineEvent(BaseModel):
    """Timeline event for LLM structured output"""
    year: int = Field(..., description="Year when this event occurs (e.g., 2030)")
    description: str = Field(..., description="Clear description of what happens")
    impact: Literal["low", "medium", "high"] = Field(
        ..., description="Impact level: low, medium, or high"
    )


class LLMScenario(BaseModel):
    """Single scenario for LLM structured output"""
    title: str = Field(..., description="Short, compelling title for this scenario")
    description: str = Field(..., description="2-3 sentence description of this future")
    category: Literal["optimistic", "pessimistic", "mixed"] = Field(
        ..., description="Scenario category: optimistic, pessimistic, or mixed"
    )
    probability: float = Field(..., description="Probability between 0.0 and 1.0")
    timeline: List[LLMTimelineEvent] = Field(..., description="5-7 chronological events")


class LLMScenariosResponse(BaseModel):
    """Complete response from LLM with multiple scenarios"""
    scenarios: List[LLMScenario] = Field(..., description="List of generated scenarios")
