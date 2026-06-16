import pytest
from backend.systems.public_opinion_system import PublicOpinionSystem
from backend.models.world_models import StructuredWorldState

@pytest.fixture
def op_system():
    return PublicOpinionSystem()

@pytest.fixture
def structured_world():
    return StructuredWorldState()

def test_get_zone(op_system):
    assert op_system.get_zone(0.1) == "stable"
    assert op_system.get_zone(0.35) == "concerned"
    assert op_system.get_zone(0.55) == "fearful"
    assert op_system.get_zone(0.71) == "angry"
    assert op_system.get_zone(0.86) == "radicalized"
    assert op_system.get_zone(0.99) == "revolutionary"

def test_nonlinear_push_opinion_small_delta(op_system, structured_world):
    # Starting at 0.1, delta is 0.05
    # new = 0.1 + 0.05 * (1 + abs(0.1 - 0.5))
    # new = 0.1 + 0.05 * 1.4 = 0.1 + 0.07 = 0.17
    
    structured_world.public_opinion["ai_safety"] = 0.1
    event = op_system.push_opinion(structured_world, "ai_safety", 0.05)
    
    assert structured_world.public_opinion["ai_safety"] == pytest.approx(0.17)
    assert event is None  # Didn't cross 0.3

def test_threshold_crossing_event(op_system, structured_world):
    # Starting at 0.25, delta is 0.05
    # new = 0.25 + 0.05 * (1 + 0.25) = 0.25 + 0.0625 = 0.3125 (crosses 0.3)
    structured_world.public_opinion["ai_safety"] = 0.25
    event = op_system.push_opinion(structured_world, "ai_safety", 0.05)
    
    assert structured_world.public_opinion["ai_safety"] == pytest.approx(0.3125)
    assert event == "Public opinion on 'ai_safety' has escalated to CONCERNED."

def test_extreme_acceleration(op_system, structured_world):
    # Near 1.0, the same delta has more impact.
    # At 0.8, delta 0.05 -> new = 0.8 + 0.05 * (1 + 0.3) = 0.8 + 0.065 = 0.865
    structured_world.public_opinion["ai_safety"] = 0.8
    event = op_system.push_opinion(structured_world, "ai_safety", 0.05)
    
    assert structured_world.public_opinion["ai_safety"] == pytest.approx(0.865)
    assert event == "Public opinion on 'ai_safety' has escalated to RADICALIZED."

def test_downward_shift(op_system, structured_world):
    # De-escalation also crosses thresholds backwards.
    # At 0.55 (fearful), delta -0.1 -> new = 0.55 - 0.1 * (1 + 0.05) = 0.55 - 0.105 = 0.445 (concerned)
    structured_world.public_opinion["ai_safety"] = 0.55
    event = op_system.push_opinion(structured_world, "ai_safety", -0.1)
    
    assert structured_world.public_opinion["ai_safety"] == pytest.approx(0.445)
    assert event == "Public opinion on 'ai_safety' has de-escalated to CONCERNED."
