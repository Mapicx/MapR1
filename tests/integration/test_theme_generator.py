import pytest
from backend.seeder.theme_generator import theme_generator
from backend.models.theme_models import ThemeSpec

@pytest.mark.asyncio
async def test_theme_generator_agi_seed():
    seed = "A near-future scenario where a tech company is on the verge of developing AGI, and governments are trying to regulate it."
    theme = await theme_generator.generate_theme(seed)
    
    assert isinstance(theme, ThemeSpec)
    assert len(theme.actor_roles) > 0
    assert len(theme.resource_types) > 0
    assert len(theme.institution_types) > 0
    assert theme.theme_name != ""

@pytest.mark.asyncio
async def test_theme_generator_cancer_seed():
    seed = "A tense medical drama where a global consortium of researchers race against time and funding cuts to cure a new form of cancer."
    theme = await theme_generator.generate_theme(seed)
    
    assert isinstance(theme, ThemeSpec)
    assert len(theme.actor_roles) > 0
    assert len(theme.core_conflicts) > 0
    assert len(theme.victory_conditions) > 0

@pytest.mark.asyncio
async def test_theme_generator_fantasy_seed():
    seed = "A high-fantasy kingdom where magic is a scarce resource and noble houses vie for the throne."
    theme = await theme_generator.generate_theme(seed)
    
    assert isinstance(theme, ThemeSpec)
    assert len(theme.core_conflicts) > 0
    assert len(theme.resource_types) > 0
    # ensure it didn't just hardcode tech stuff
    resources_str = str(theme.resource_types).lower()
    assert "magic" in resources_str or "mana" in resources_str or "gold" in resources_str or "land" in resources_str or "crystal" in resources_str or "spell" in resources_str
