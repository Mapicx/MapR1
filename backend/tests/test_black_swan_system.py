import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from backend.systems.black_swan_system import BlackSwanSystem
from backend.models.world_models import StructuredWorldState

class MockWorldState:
    def __init__(self, state_dict, project_id):
        self.id = uuid4()
        self.project_id = project_id
        self.state = state_dict

@pytest.fixture
def black_swan_system():
    return BlackSwanSystem()

@pytest.fixture
def mock_world_state():
    structured = StructuredWorldState(
        public_opinion={"ai_trust": 0.5, "social_stability": 0.5},
        market_conditions={"tech": 0.5, "finance": 0.5},
        regulatory_pressure={"tech": 0.2},
        recent_events=[]
    )
    ws = MockWorldState(state_dict=structured.to_dict(), project_id=uuid4())
    return ws

@pytest.fixture
def mock_db():
    return AsyncMock()

def test_events_are_rare(black_swan_system, mock_world_state, mock_db):
    """Test that rolling naturally almost never triggers an event."""
    triggered_count = 0
    # Roll 100 times, probability of 0.005 max means it's unlikely to fire many
    for _ in range(100):
        ev = black_swan_system.roll(mock_world_state, 1, mock_world_state.project_id, mock_db)
        if ev:
            triggered_count += 1
            
    # Should be rare, not impossible, but extremely likely to be less than 5
    assert triggered_count < 10

def test_forced_trigger_mutates_state(black_swan_system, mock_world_state, mock_db):
    """Test that a fired event successfully mutates the state."""
    
    # We will temporarily force the probability of the first event to 1.0
    original_prob = black_swan_system.EVENTS[0]["probability"]
    black_swan_system.EVENTS[0]["probability"] = 1.0
    
    event_fired = black_swan_system.roll(mock_world_state, 1, mock_world_state.project_id, mock_db)
    
    # Restore
    black_swan_system.EVENTS[0]["probability"] = original_prob
    
    assert event_fired is not None
    assert event_fired["name"] == "agi_manipulates_stocks"
    
    # State should be updated
    structured = StructuredWorldState.from_dict(mock_world_state.state)
    
    # original was 0.5, impact is -0.8 on tech -> 0.0
    assert structured.market_conditions["tech"] == 0.0
    
    # recent_events should contain the black swan event
    assert len(structured.recent_events) >= 1
    assert structured.recent_events[0].action == "black_swan"
    assert structured.recent_events[0].visibility == 1.0
    assert "BLACK SWAN:" in structured.recent_events[0].outcome
    
    # db.add should have been called
    mock_db.add.assert_called_once_with(mock_world_state)

def test_public_opinion_thresholds(black_swan_system, mock_world_state, mock_db):
    """Test that black swans can trigger public opinion threshold events."""
    
    # Force the 'ai_generated_religion_emerges' event
    religion_event = next(ev for ev in black_swan_system.EVENTS if ev["name"] == "ai_generated_religion_emerges")
    
    original_prob = religion_event["probability"]
    religion_event["probability"] = 1.0
    
    # Make sure we hit the first event by temporarily disabling others
    with patch.object(black_swan_system, 'EVENTS', [religion_event]):
        black_swan_system.roll(mock_world_state, 1, mock_world_state.project_id, mock_db)
        
    religion_event["probability"] = original_prob
    
    structured = StructuredWorldState.from_dict(mock_world_state.state)
    
    # Public opinion ai_trust starts at 0.5, delta is +0.4 -> new is 0.5 + 0.4 * (1.0 + 0) = 0.9 (radicalized)
    assert structured.public_opinion["ai_trust"] == pytest.approx(0.9)
    
    # Check that both the black swan and the opinion shifts were logged
    events = structured.recent_events
    assert len(events) == 3
    assert events[0].action == "black_swan"
    assert events[1].action == "opinion_shift"
    assert "RADICALIZED" in events[1].outcome
    assert events[2].action == "opinion_shift"
    assert "STABLE" in events[2].outcome
