import pytest
from backend.models.theme_models import ThemeSpec
from backend.seeder.theme_compiler import theme_compiler
from backend.models.compiled_model import CompiledTheme

def create_valid_theme_spec(name="Generic"):
    return ThemeSpec(
        theme_name=name,
        theme_summary="A summary",
        core_conflicts=["Conflict B", "Conflict A"],
        actor_roles=["Role B", "Role A"],
        resource_types=["Resource B", "Resource A"],
        institution_types=["Institution B", "Institution A"],
        event_templates=["Event B", "Event A"],
        vocabulary_map={"money": "credits"},
        victory_conditions=["Win B", "Win A"],
        failure_conditions=["Fail B", "Fail A"],
        narrative_tone="Dark",
        risk_profile="High"
    )

def test_compiler_normalization_and_sorting():
    spec = create_valid_theme_spec()
    compiled = theme_compiler.compile(spec)
    
    assert isinstance(compiled, CompiledTheme)
    
    # Verify deterministic sorting (A comes before B)
    assert compiled.resources["resource_0"] == "Resource A"
    assert compiled.resources["resource_1"] == "Resource B"
    assert compiled.roles["role_0"] == "Role A"
    assert compiled.roles["role_1"] == "Role B"

def test_compiler_rejects_invalid_theme():
    spec = create_valid_theme_spec()
    # Invalidate by emptying resources
    spec.resource_types = []
    
    with pytest.raises(ValueError, match="missing required resource items"):
        theme_compiler.compile(spec)

def test_compiler_structural_equivalency():
    agi_spec = create_valid_theme_spec("AGI")
    agi_spec.resource_types = ["Compute", "Data"]
    
    fantasy_spec = create_valid_theme_spec("Fantasy")
    fantasy_spec.resource_types = ["Mana", "Gold"]
    
    agi_compiled = theme_compiler.compile(agi_spec)
    fantasy_compiled = theme_compiler.compile(fantasy_spec)
    
    # Both should have exactly the same keys for resources despite different content
    assert set(agi_compiled.resources.keys()) == set(fantasy_compiled.resources.keys())
    assert agi_compiled.resources.keys() == {"resource_0", "resource_1"}
    
    # Verify sorting was applied
    assert agi_compiled.resources["resource_0"] == "Compute"
    assert fantasy_compiled.resources["resource_0"] == "Gold"
