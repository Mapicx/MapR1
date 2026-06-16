import pytest
from pydantic import ValidationError
from backend.models.theme_models import ThemeSpec

def test_theme_spec_valid():
    """Test that a valid theme object can be created."""
    valid_data = {
        "theme_name": "Space Colonization",
        "theme_summary": "Humanity expanding to other planets.",
        "core_conflicts": ["Resource scarcity", "Hostile environments"],
        "actor_roles": ["Astronaut", "Engineer", "Politician"],
        "resource_types": ["Oxygen", "Fuel", "Water"],
        "institution_types": ["Space Agency", "Megacorporation"],
        "event_templates": ["Meteor strike", "New technology discovered"],
        "vocabulary_map": {"money": "credits", "person": "colonist"},
        "victory_conditions": ["Establish a self-sustaining colony"],
        "failure_conditions": ["Colony runs out of oxygen"],
        "narrative_tone": "Hopeful but dangerous",
        "risk_profile": "High"
    }
    
    theme = ThemeSpec(**valid_data)
    assert theme.theme_name == "Space Colonization"
    assert theme.vocabulary_map["money"] == "credits"

def test_theme_spec_missing_required_fields():
    """Test that missing required fields raises a ValidationError."""
    # Missing 'theme_name'
    invalid_data = {
        "theme_summary": "Humanity expanding to other planets.",
        "core_conflicts": ["Resource scarcity", "Hostile environments"],
        "actor_roles": ["Astronaut", "Engineer", "Politician"],
        "resource_types": ["Oxygen", "Fuel", "Water"],
        "institution_types": ["Space Agency", "Megacorporation"],
        "event_templates": ["Meteor strike", "New technology discovered"],
        "vocabulary_map": {"money": "credits", "person": "colonist"},
        "victory_conditions": ["Establish a self-sustaining colony"],
        "failure_conditions": ["Colony runs out of oxygen"],
        "narrative_tone": "Hopeful but dangerous",
        "risk_profile": "High"
    }
    
    with pytest.raises(ValidationError) as exc_info:
        ThemeSpec(**invalid_data)
    
    assert "theme_name" in str(exc_info.value)
    
    # Empty data
    with pytest.raises(ValidationError) as exc_info:
        ThemeSpec()
        
    errors = str(exc_info.value)
    assert "theme_name" in errors
    assert "theme_summary" in errors
    assert "core_conflicts" in errors
    assert "actor_roles" in errors
    assert "resource_types" in errors
    assert "institution_types" in errors
    assert "event_templates" in errors
    assert "vocabulary_map" in errors
    assert "victory_conditions" in errors
    assert "failure_conditions" in errors
    assert "narrative_tone" in errors
    assert "risk_profile" in errors
