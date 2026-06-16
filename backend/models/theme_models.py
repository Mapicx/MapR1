from pydantic import BaseModel, Field
from typing import List, Dict

class ThemeSpec(BaseModel):
    """
    A canonical, domain-agnostic schema for representing any simulation dream theme.
    
    This schema is designed to represent generic scenario templates without any domain-specific 
    assumptions. It is purely abstract and can be applied to any simulation context. 
    AGI development and cancer research are only example themes, not hardcoded limits.
    """
    theme_name: str = Field(..., description="The name of the theme.")
    theme_summary: str = Field(..., description="A summary of the theme.")
    core_conflicts: List[str] = Field(..., description="The main conflicts or challenges in this theme.")
    actor_roles: List[str] = Field(..., description="The roles that actors can take in this theme.")
    resource_types: List[str] = Field(..., description="Types of resources relevant to this theme.")
    institution_types: List[str] = Field(..., description="Types of institutions relevant to this theme.")
    event_templates: List[str] = Field(..., description="Templates for events that can occur.")
    vocabulary_map: Dict[str, str] = Field(..., description="A mapping of general terms to theme-specific vocabulary.")
    victory_conditions: List[str] = Field(..., description="Conditions for winning or succeeding in this theme.")
    failure_conditions: List[str] = Field(..., description="Conditions for failing in this theme.")
    narrative_tone: str = Field(..., description="The general tone of the narrative (e.g., optimistic, grim).")
    risk_profile: str = Field(..., description="The overall risk profile or volatility of the theme.")
