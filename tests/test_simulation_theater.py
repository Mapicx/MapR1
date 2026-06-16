import asyncio
import sys
from datetime import datetime
from uuid import uuid4
from loguru import logger

sys.path.insert(0, ".")

from backend.models.action_models import ActionResponse, ActionType
from backend.models.world_models import StructuredWorldState
from backend.theater.theater_models import TensionMetrics, TensionPhase, PacingMode
from backend.theater.tension_tracker import tension_tracker
from backend.theater.pacing_engine import pacing_engine
from backend.theater.divergence_detector import divergence_detector

def _create_mock_action(action_type: ActionType, success: bool, confidence: float, impact_side_effects: int = 0) -> ActionResponse:
    return ActionResponse(
        id=uuid4(),
        agent_id=uuid4(),
        agent_name="MockAgent",
        action_type=action_type.value,
        description=f"Performed {action_type.value}",
        reasoning="Test reasoning",
        confidence=confidence,
        executed=True,
        success=success,
        outcome="Test outcome",
        impact={"side_effects": ["effect"] * impact_side_effects},
        simulation_step=1,
        created_at=datetime.utcnow()
    )

async def test_tension_tracker():
    logger.info("=== Testing Tension Tracker ===")
    
    # 1. Lull phase (neutral/wait actions)
    actions_lull = [
        _create_mock_action(ActionType.WAIT, True, 0.9),
        _create_mock_action(ActionType.OBSERVE, True, 0.8)
    ]
    world = StructuredWorldState()
    
    t1 = tension_tracker.compute_tension(1, actions_lull, world, [])
    logger.info(f"Step 1 (Lull) Tension: {t1.overall_tension:.2f} - Phase: {t1.phase.value}")
    assert t1.overall_tension < 0.3
    
    # 2. Rising action (business/political moves)
    actions_rising = [
        _create_mock_action(ActionType.EXPAND_BUSINESS, True, 0.8, 1),
        _create_mock_action(ActionType.PROPOSE_POLICY, False, 0.6)
    ]
    t2 = tension_tracker.compute_tension(2, actions_rising, world, [t1])
    logger.info(f"Step 2 (Rising) Tension: {t2.overall_tension:.2f} - Phase: {t2.phase.value}")
    assert t2.overall_tension > t1.overall_tension
    
    # 3. Climax (attacks, sabotage)
    actions_climax = [
        _create_mock_action(ActionType.ATTACK, True, 0.9, 2),
        _create_mock_action(ActionType.SABOTAGE, False, 0.8, 1),
        _create_mock_action(ActionType.BETRAY, True, 0.9, 3)
    ]
    t3 = tension_tracker.compute_tension(3, actions_climax, world, [t1, t2])
    logger.info(f"Step 3 (Climax) Tension: {t3.overall_tension:.2f} - Phase: {t3.phase.value}")
    assert t3.overall_tension > 0.5
    
    logger.success("Tension Tracker tests passed!")
    return [t1, t2, t3]

async def test_pacing_engine(history):
    logger.info("=== Testing Pacing Engine ===")
    
    # Check lull pacing
    pacing_lull = pacing_engine.get_pacing_recommendation(PacingMode.AUTO_DRAMATIC, history[0], [])
    logger.info(f"Lull Pacing: {pacing_lull.delay_seconds}s delay, Pause: {pacing_lull.should_pause}")
    assert pacing_lull.delay_seconds < 2.0
    
    # Check climax pacing
    history[2].is_climax_candidate = True
    history[2].overall_tension = 0.85
    pacing_climax = pacing_engine.get_pacing_recommendation(PacingMode.AUTO_DRAMATIC, history[2], history[:2])
    logger.info(f"Climax Pacing: {pacing_climax.delay_seconds}s delay, Pause: {pacing_climax.should_pause}")
    assert pacing_climax.should_pause or pacing_climax.delay_seconds == 0.0
    
    logger.success("Pacing Engine tests passed!")

async def test_divergence_detector(history):
    logger.info("=== Testing Divergence Detector ===")
    
    # High confidence failed action
    actions = [
        _create_mock_action(ActionType.ATTACK, False, 0.95, 2)
    ]
    world = StructuredWorldState()
    
    # Force a climax tension so we definitely trigger divergence
    tension = history[2]
    tension.is_climax_candidate = True
    
    divergence = divergence_detector.detect_divergence(4, actions, tension, world)
    logger.info(f"Detected Divergence: {divergence.description if divergence else 'None'}")
    
    assert divergence is not None
    assert len(divergence.branches) > 0
    for i, b in enumerate(divergence.branches):
        logger.info(f"  Branch {i+1}: {b.label} -> {b.description}")
        
    logger.success("Divergence Detector tests passed!")

async def run_all_tests():
    logger.info("Starting Simulation Theater Component Tests")
    
    try:
        history = await test_tension_tracker()
        await test_pacing_engine(history)
        await test_divergence_detector(history)
        logger.success("All Theater component tests passed successfully!")
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during tests: {e}")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
