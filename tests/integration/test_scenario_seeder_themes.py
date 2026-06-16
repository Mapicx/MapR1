import pytest
from backend.seeder.seed_models import GenerateRequest
from backend.seeder.theme_generator import theme_generator
from backend.seeder.theme_compiler import theme_compiler
from backend.seeder.scenario_seeder import scenario_seeder

@pytest.mark.asyncio
async def test_high_fantasy_seed_leakage():
    # Generate the theme spec
    prompt = "A high fantasy world where elves, dwarves, and wizards fight over magical leylines and ancient artifacts in the kingdom of Eldoria."
    theme_spec = await theme_generator.generate_theme(prompt)
    
    # Compile it
    compiled_theme = theme_compiler.compile(theme_spec)
    
    # Generate the scenario
    request = GenerateRequest(prompt=prompt)
    seed = await scenario_seeder.generate(request, theme=compiled_theme)
    
    def contains_forbidden(text):
        if not isinstance(text, str):
            return False
        text_lower = text.lower()
        forbidden = ["ceo", "tech company", "stock market", "regulatory", "agi", "cancer"]
        for word in forbidden:
            if word in text_lower:
                return True
        return False
        
    # Check entities
    for entity in seed.entities:
        assert not contains_forbidden(entity.name), f"Entity name '{entity.name}' leaked domain terms."
        assert not contains_forbidden(entity.description), f"Entity description leaked domain terms."
        assert not contains_forbidden(entity.type), f"Entity type '{entity.type}' leaked domain terms."
        for v in entity.attributes.values():
            assert not contains_forbidden(v), f"Entity attribute leaked domain terms."
            
    # Check agents
    for agent in seed.agents:
        assert not contains_forbidden(agent.name), f"Agent name '{agent.name}' leaked domain terms."
        assert not contains_forbidden(agent.role), f"Agent role '{agent.role}' leaked domain terms."
        assert not contains_forbidden(agent.agent_type), f"Agent type '{agent.agent_type}' leaked domain terms."
        assert not contains_forbidden(agent.backstory), f"Agent backstory leaked domain terms."
        assert not contains_forbidden(agent.secret), f"Agent secret leaked domain terms."

    # Verify that canonical keys are actually used
    # E.g., agent_type should be role_0, role_1, etc.
    for agent in seed.agents:
        assert agent.agent_type.startswith("role_"), f"Agent type '{agent.agent_type}' is not a canonical key."

@pytest.mark.asyncio
async def test_cyberpunk_seed_leakage():
    # Generate the theme spec
    prompt = "A gritty cyberpunk dystopia where megacorporations control the world, hackers steal data, and street samurais fight for survival."
    theme_spec = await theme_generator.generate_theme(prompt)
    
    # Compile it
    compiled_theme = theme_compiler.compile(theme_spec)
    
    # Generate the scenario
    request = GenerateRequest(prompt=prompt)
    seed = await scenario_seeder.generate(request, theme=compiled_theme)
    
    def contains_forbidden(text):
        if not isinstance(text, str):
            return False
        text_lower = text.lower()
        forbidden = ["magic", "wizard", "elves", "cancer", "agi", "biotech"]
        for word in forbidden:
            if word in text_lower:
                return True
        return False
        
    # Check entities
    for entity in seed.entities:
        assert not contains_forbidden(entity.name), f"Entity name '{entity.name}' leaked domain terms."
        assert not contains_forbidden(entity.description), f"Entity description leaked domain terms."
        assert not contains_forbidden(entity.type), f"Entity type '{entity.type}' leaked domain terms."
            
    # Check agents
    for agent in seed.agents:
        assert not contains_forbidden(agent.name), f"Agent name '{agent.name}' leaked domain terms."
        assert not contains_forbidden(agent.role), f"Agent role '{agent.role}' leaked domain terms."
        assert not contains_forbidden(agent.agent_type), f"Agent type '{agent.agent_type}' leaked domain terms."

    # Verify that canonical keys are actually used
    for agent in seed.agents:
        assert agent.agent_type.startswith("role_"), f"Agent type '{agent.agent_type}' is not a canonical key."
