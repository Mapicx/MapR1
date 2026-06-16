import sys
import asyncio
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, ".")

from loguru import logger
from sqlalchemy import select
from backend.core.database import get_db, init_db
from backend.models.db_models import Project
from backend.models.world_models import WorldState, StructuredWorldState
from backend.models.delayed_effects import ScheduledEvent
from backend.systems.delayed_effect_system import DelayedEffectSystem

async def test_schedule_and_fire():
    """Test scheduling and firing delayed events."""
    logger.info("=" * 80)
    logger.info("TEST: Delayed Consequences System")
    logger.info("=" * 80)

    # Initialize tables
    await init_db()
    
    delayed_system = DelayedEffectSystem()

    async for db in get_db():
        try:
            passed_test = True
            # 1. Setup Test Data
            project_id = uuid4()
            project = Project(id=project_id, name="Test Delayed Project", description="Test")
            db.add(project)
            
            structured = StructuredWorldState()
            structured.public_opinion["ai_safety"] = 0.5
            structured.regulatory_pressure["techcorp"] = 0.1
            
            world_state = WorldState(
                id=uuid4(),
                project_id=project_id,
                state=structured.to_dict(),
            )
            db.add(world_state)
            await db.commit()

            # 2. Test Scheduling
            logger.info("Testing scheduling...")
            await delayed_system.schedule(
                db=db,
                project_id=project_id,
                trigger_turn=3,
                event_type="test_event",
                description="A test consequence.",
                impact_data={"public_opinion": {"ai_safety": -0.2}, "regulatory_pressure": {"techcorp": 0.3}},
            )

            # Verify it's in DB
            result = await db.execute(select(ScheduledEvent).where(ScheduledEvent.project_id == project_id))
            events = result.scalars().all()
            assert len(events) == 1
            assert events[0].is_fired is False
            assert events[0].trigger_turn == 3
            logger.success("✓ Event scheduled successfully")

            # 3. Test Early Firing (Should Not Fire)
            logger.info("Testing early fire prevention (Step 2)...")
            await delayed_system.check_and_fire(db, current_step=2, project_id=project_id, world_state=world_state)
            
            # Verify still unfired
            await db.refresh(events[0])
            assert events[0].is_fired is False
            
            # Verify world state unchanged
            await db.refresh(world_state)
            restored_state = StructuredWorldState.from_dict(world_state.state)
            assert restored_state.public_opinion["ai_safety"] == 0.5
            assert len(restored_state.recent_events) == 0
            logger.success("✓ Event did not fire early")

            # 4. Test Firing at Correct Step
            logger.info("Testing correct firing (Step 3)...")
            await delayed_system.check_and_fire(db, current_step=3, project_id=project_id, world_state=world_state)

            # Verify fired
            await db.refresh(events[0])
            assert events[0].is_fired is True
            assert events[0].fired_at is not None

            # Verify world state mutated
            await db.refresh(world_state)
            restored_state = StructuredWorldState.from_dict(world_state.state)
            assert restored_state.public_opinion["ai_safety"] == 0.3  # 0.5 - 0.2
            assert restored_state.regulatory_pressure["techcorp"] == 0.4  # 0.1 + 0.3
            assert len(restored_state.recent_events) == 1
            assert restored_state.recent_events[0].action == "test_event"
            logger.success("✓ Event fired and mutated world state successfully")

            # 5. Test Double Fire Prevention
            logger.info("Testing double fire prevention (Step 4)...")
            await delayed_system.check_and_fire(db, current_step=4, project_id=project_id, world_state=world_state)
            
            # Verify events didn't grow
            await db.refresh(world_state)
            restored_state = StructuredWorldState.from_dict(world_state.state)
            assert len(restored_state.recent_events) == 1  # Still 1
            logger.success("✓ Event did not fire twice")

        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            passed_test = False
        finally:
            # Cleanup
            await db.execute(select(ScheduledEvent).where(ScheduledEvent.project_id == project_id))
            await db.delete(project)  # Cascade will delete world_state and scheduled_events
            await db.commit()
            return passed_test

async def run_all_tests():
    passed = await test_schedule_and_fire()
    if passed:
        logger.success("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n❌ TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
