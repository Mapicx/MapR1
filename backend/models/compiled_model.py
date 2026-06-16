from pydantic import BaseModel, Field
from typing import Dict

class CompiledTheme(BaseModel):
    """
    The deterministic, canonical internal representation of a theme.
    
    This schema is safely consumed by the simulation core. All domain-specific strings
    from the LLM are mapped to stable, abstract keys (e.g., 'resource_0', 'role_1') 
    so the engine never relies on arbitrary text for logic.
    """
    id: str = Field(..., description="Unique identifier for the compiled theme.")
    theme_name: str = Field(..., description="The name of the theme.")
    theme_summary: str = Field(..., description="A summary of the theme.")
    narrative_tone: str = Field(..., description="The general tone of the narrative.")
    risk_profile: str = Field(..., description="The overall risk profile or volatility.")
    
    # Mappings from internal generic key to domain-specific string
    conflicts: Dict[str, str] = Field(..., description="Mapping of 'conflict_N' to domain conflict")
    roles: Dict[str, str] = Field(..., description="Mapping of 'role_N' to domain role")
    resources: Dict[str, str] = Field(..., description="Mapping of 'resource_N' to domain resource")
    institutions: Dict[str, str] = Field(..., description="Mapping of 'institution_N' to domain institution")
    events: Dict[str, str] = Field(..., description="Mapping of 'event_N' to domain event template")
    victory_conditions: Dict[str, str] = Field(..., description="Mapping of 'victory_N' to condition")
    failure_conditions: Dict[str, str] = Field(..., description="Mapping of 'failure_N' to condition")
    
    # Generic vocabulary mapping
    vocabulary_map: Dict[str, str] = Field(..., description="Mapping of standard terms to theme terms")
