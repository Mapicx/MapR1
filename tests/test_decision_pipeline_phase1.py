"""
Test script for Decision Pipeline Phase 1

Tests:
1. Fact-to-Action Mapping
2. Repetition Prevention (Cooldowns)
3. Personality Filtering
4. Goal Alignment Ranking
5. Integration Test (Full Simulation)
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime

# Add backend to path
sys.path.insert(0, ".")

from backend.core.database import get_db
from backend.models.agent_models import Agent, Personality
from backend.models.goal_models import Goal
from backend.models.action_models import AgentAction, CandidateAction, RecentAction
from backend.agents.candidate_generator import CandidateActionGenerator
from backend.agents.action_cooldown import ActionCooldownManager
from backend.repositories.project_repository import ProjectRepository
from backend.repositories.agent_repository import AgentRepository
from loguru import logger


# ── Test 1: Fact-to-Action Mapping ──────────────────────────────────────────

async def test_fact_to_action_mapping():
    """Test that discovered facts generate appropriate candidate actions"""
    logger.info("=" * 80)
    logger.info("TEST 1: Fact-to-Action Mapping")
    logger.info("=" * 80)
    
    async for db in get_db():
        try:
            # Create test project and agent
            project_repo = ProjectRepository(db)
            project = await project_repo.create_project(
                name="Test Decision Pipeline Phase 1",
                description="Testing context-aware action generation"
            )
            
            agent_repo = AgentRepository(db)
            agent = await agent_repo.create_agent(
                project_id=project.id,
                name="Sarah Chen",
                agent_type="ceo",
                role="CEO of TechCorp",
                personality=Personality(
                    ambition=0.9,
                    risk_tolerance=0.7,
                    morality=0.6,
                    empathy=0.5,
                ).dict(),
            )
            
            # Create a goal
            goal = Goal(
                id=uuid4(),
                agent_id=agent.id,
                description="Increase market share and dominate the industry",
                goal_type="wealth",
                priority=0.9,
                progress=0.0,
                knowledge_score=0.7,  # Above threshold
                status="active",
                created_at=datetime.utcnow(),
            )
            db.add(goal)
            await db.commit()
            
            # Test facts
            discovered_facts = [
                "RivalCorp is burning cash at $2M/month and has only 8 months of runway left",
                "TechCorp's supply chain relies on a single supplier in Vietnam — a critical vulnerability",
                "A government contract worth $50M is up for bid next quarter",
            ]
            
            # Generate candidates
            generator = CandidateActionGenerator()
            candidates = await generator.generate_candidates(
                db=db,
                agent=agent,
                discovered_facts=discovered_facts,
                active_goals=[goal],
                relationships=[],
                world_state=None,
                recently_attempted=[],
            )
            
            logger.info(f"\n✓ Generated {len(candidates)} candidates from {len(discovered_facts)} facts")
            
            # Verify expected actions are present
            expected_keywords = ["rivalcorp", "supply", "contract", "bid"]
            found_keywords = []
            
            for candidate in candidates:
                logger.info(f"\n  Action: {candidate.display_name}")
                logger.info(f"  Source: {candidate.source_fact[:60]}...")
                logger.info(f"  Alignment: {candidate.goal_alignment:.2f} | Risk: {candidate.risk_level:.2f}")
                
                for keyword in expected_keywords:
                    if keyword in candidate.action_name.lower():
                        found_keywords.append(keyword)
            
            # Verify we got relevant actions
            assert len(candidates) > 0, "Should generate at least one candidate"
            assert len(found_keywords) > 0, f"Should find at least one expected keyword, found: {found_keywords}"
            
            # Verify NO generic actions like "expand business operations"
            generic_actions = [c for c in candidates if "expand business" in c.display_name.lower()]
            assert len(generic_actions) == 0, "Should NOT generate generic actions"
            
            logger.success("\n✓ TEST 1 PASSED: Fact-to-action mapping works correctly")
            
            # Cleanup
            await project_repo.delete_project(project.id)
            await db.commit()
            
        except Exception as e:
            logger.error(f"TEST 1 FAILED: {e}")
            raise
        finally:
            break


# ── Test 2: Repetition Prevention ───────────────────────────────────────────

async def test_repetition_prevention():
    """Test that cooldown system blocks repeated actions"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Repetition Prevention (Cooldowns)")
    logger.info("=" * 80)
    
    async for db in get_db():
        try:
            # Create test project and agent
            project_repo = ProjectRepository(db)
            project = await project_repo.create_project(
                name="Test Cooldowns",
                description="Testing action cooldown system"
            )
            
            agent_repo = AgentRepository(db)
            agent = await agent_repo.create_agent(
                project_id=project.id,
                name="Test Agent",
                agent_type="ceo",
                role="CEO",
                personality=Personality().dict(),
            )
            
            # Create recent actions
            recent_action = AgentAction(
                id=uuid4(),
                agent_id=agent.id,
                project_id=project.id,
                simulation_step=5,
                action_type="exploit_rivalcorp_supply_chain_weakness",
                description="Exploited supply chain",
                reasoning="Test",
                confidence=0.8,
                executed=True,
                success=True,
                outcome="Success",
                impact={},
                created_at=datetime.utcnow(),
            )
            db.add(recent_action)
            await db.commit()
            
            # Create candidate actions (including the one just attempted)
            candidates = [
                CandidateAction(
                    action_name="exploit_rivalcorp_supply_chain_weakness",
                    display_name="Exploit RivalCorp supply chain weakness",
                    source_fact="RivalCorp has supply chain issues",
                    goal_alignment=0.8,
                    risk_level=0.6,
                ),
                CandidateAction(
                    action_name="bid_on_government_contract",
                    display_name="Bid on government contract",
                    source_fact="Government contract available",
                    goal_alignment=0.7,
                    risk_level=0.3,
                ),
            ]
            
            # Load recent actions
            cooldown_mgr = ActionCooldownManager()
            recent_actions = await cooldown_mgr.get_recent_actions(db, agent.id, lookback_steps=5)
            
            logger.info(f"\n✓ Loaded {len(recent_actions)} recent actions")
            
            # Apply cooldowns at step 6 (1 step after the action)
            current_step = 6
            filtered = cooldown_mgr.apply_cooldowns(candidates, recent_actions, current_step)
            
            logger.info(f"\n✓ Cooldown filter: {len(candidates)} -> {len(filtered)} candidates")
            
            # Verify the exact action is blocked
            blocked_action_names = [c.action_name for c in candidates if c not in filtered]
            logger.info(f"  Blocked actions: {blocked_action_names}")
            
            assert "exploit_rivalcorp_supply_chain_weakness" in blocked_action_names, \
                "Should block exact action within cooldown period"
            
            # Verify other actions are still available
            assert len(filtered) > 0, "Should have at least one action available"
            assert any("bid" in c.action_name for c in filtered), \
                "Should keep unrelated actions"
            
            # Test at step 9 (4 steps after, cooldown expired)
            current_step = 9
            filtered_later = cooldown_mgr.apply_cooldowns(candidates, recent_actions, current_step)
            
            logger.info(f"\n✓ At step 9 (cooldown expired): {len(filtered_later)} candidates available")
            
            assert len(filtered_later) == len(candidates), \
                "All actions should be available after cooldown expires"
            
            logger.success("\n✓ TEST 2 PASSED: Cooldown system works correctly")
            
            # Cleanup
            await project_repo.delete_project(project.id)
            await db.commit()
            
        except Exception as e:
            logger.error(f"TEST 2 FAILED: {e}")
            raise
        finally:
            break


# ── Test 3: Personality Filtering ───────────────────────────────────────────

async def test_personality_filtering():
    """Test that personality traits filter inappropriate actions"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Personality Filtering")
    logger.info("=" * 80)
    
    async for db in get_db():
        try:
            # Create test project
            project_repo = ProjectRepository(db)
            project = await project_repo.create_project(
                name="Test Personality",
                description="Testing personality-based filtering"
            )
            
            agent_repo = AgentRepository(db)
            
            # Create high-morality activist
            activist = await agent_repo.create_agent(
                project_id=project.id,
                name="Ethical Activist",
                agent_type="activist",
                role="Environmental Activist",
                personality=Personality(
                    morality=0.9,  # High morality
                    empathy=0.9,   # High empathy
                    risk_tolerance=0.3,  # Low risk tolerance
                ).dict(),
            )
            
            # Create goal
            goal = Goal(
                id=uuid4(),
                agent_id=activist.id,
                description="Expose corporate wrongdoing",
                goal_type="ideology",
                priority=0.9,
                progress=0.0,
                knowledge_score=0.7,
                status="active",
                created_at=datetime.utcnow(),
            )
            db.add(goal)
            await db.commit()
            
            # Test facts that could generate both ethical and unethical actions
            discovered_facts = [
                "TechCorp has evidence of environmental violations",
                "A whistleblower inside TechCorp has damaging information",
                "TechCorp's supply chain has vulnerabilities that could be exploited",
            ]
            
            # Generate candidates
            generator = CandidateActionGenerator()
            candidates = await generator.generate_candidates(
                db=db,
                agent=activist,
                discovered_facts=discovered_facts,
                active_goals=[goal],
                relationships=[],
                world_state=None,
                recently_attempted=[],
            )
            
            logger.info(f"\n✓ Generated {len(candidates)} candidates for high-morality activist")
            
            # Verify ethical actions are present
            ethical_actions = [c for c in candidates if any(
                keyword in c.action_name.lower() 
                for keyword in ["expose", "media", "legal", "complaint", "whistleblower"]
            )]
            
            # Verify unethical actions are blocked
            unethical_actions = [c for c in candidates if any(
                keyword in c.action_name.lower()
                for keyword in ["sabotage", "exploit", "attack"]
            )]
            
            logger.info(f"  Ethical actions: {len(ethical_actions)}")
            logger.info(f"  Unethical actions: {len(unethical_actions)}")
            
            for candidate in candidates:
                logger.info(f"  - {candidate.display_name} (risk: {candidate.risk_level:.2f})")
            
            assert len(ethical_actions) > 0, "Should have ethical actions available"
            assert len(unethical_actions) == 0, "Should block unethical actions for high-morality agent"
            
            logger.success("\n✓ TEST 3 PASSED: Personality filtering works correctly")
            
            # Cleanup
            await project_repo.delete_project(project.id)
            await db.commit()
            
        except Exception as e:
            logger.error(f"TEST 3 FAILED: {e}")
            raise
        finally:
            break


# ── Test 4: Goal Alignment Ranking ──────────────────────────────────────────

async def test_goal_alignment_ranking():
    """Test that actions are ranked by goal alignment"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Goal Alignment Ranking")
    logger.info("=" * 80)
    
    async for db in get_db():
        try:
            # Create test project and agent
            project_repo = ProjectRepository(db)
            project = await project_repo.create_project(
                name="Test Goal Alignment",
                description="Testing goal-based ranking"
            )
            
            agent_repo = AgentRepository(db)
            agent = await agent_repo.create_agent(
                project_id=project.id,
                name="CEO",
                agent_type="ceo",
                role="CEO",
                personality=Personality().dict(),
            )
            
            # Create wealth goal
            goal = Goal(
                id=uuid4(),
                agent_id=agent.id,
                description="Maximize company wealth",
                goal_type="wealth",  # Wealth goal
                priority=0.9,
                progress=0.0,
                knowledge_score=0.7,
                status="active",
                created_at=datetime.utcnow(),
            )
            db.add(goal)
            await db.commit()
            
            # Facts that generate different types of actions
            discovered_facts = [
                "A government contract worth $50M is up for bid",  # Wealth-aligned
                "RivalCorp's board is divided and vulnerable",  # Power-aligned
                "Media is interested in corporate accountability",  # Ideology-aligned
            ]
            
            # Generate candidates
            generator = CandidateActionGenerator()
            candidates = await generator.generate_candidates(
                db=db,
                agent=agent,
                discovered_facts=discovered_facts,
                active_goals=[goal],
                relationships=[],
                world_state=None,
                recently_attempted=[],
            )
            
            logger.info(f"\n✓ Generated {len(candidates)} candidates")
            logger.info("\nRanking by goal alignment (wealth goal):")
            
            for i, candidate in enumerate(candidates, 1):
                logger.info(
                    f"  {i}. {candidate.display_name} "
                    f"(alignment: {candidate.goal_alignment:.2f})"
                )
            
            # Verify wealth-aligned actions rank higher
            if len(candidates) >= 2:
                top_candidate = candidates[0]
                # Top candidate should have high alignment
                assert top_candidate.goal_alignment >= 0.3, \
                    f"Top candidate should have decent alignment, got {top_candidate.goal_alignment}"
                
                # Verify ranking is descending
                for i in range(len(candidates) - 1):
                    assert candidates[i].goal_alignment >= candidates[i+1].goal_alignment, \
                        "Candidates should be sorted by alignment (descending)"
            
            logger.success("\n✓ TEST 4 PASSED: Goal alignment ranking works correctly")
            
            # Cleanup
            await project_repo.delete_project(project.id)
            await db.commit()
            
        except Exception as e:
            logger.error(f"TEST 4 FAILED: {e}")
            raise
        finally:
            break


# ── Main Test Runner ────────────────────────────────────────────────────────

async def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "=" * 80)
    logger.info("DECISION PIPELINE PHASE 1 - TEST SUITE")
    logger.info("=" * 80)
    
    tests = [
        ("Fact-to-Action Mapping", test_fact_to_action_mapping),
        ("Repetition Prevention", test_repetition_prevention),
        ("Personality Filtering", test_personality_filtering),
        ("Goal Alignment Ranking", test_goal_alignment_ranking),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            logger.error(f"\n✗ {test_name} FAILED: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        logger.success("\n🎉 ALL TESTS PASSED!")
    else:
        logger.error(f"\n❌ {failed} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
