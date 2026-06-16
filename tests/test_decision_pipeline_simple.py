"""
Simple unit tests for Decision Pipeline Phase 1 components
Tests the core logic without database dependencies
"""

import sys
sys.path.insert(0, ".")

from backend.models.action_models import CandidateAction, RecentAction
from backend.agents.candidate_generator import CandidateActionGenerator
from backend.agents.action_cooldown import ActionCooldownManager
from backend.models.agent_models import Agent, Personality
from uuid import uuid4
from datetime import datetime
from loguru import logger


def test_fact_extraction():
    """Test that facts are correctly parsed into actions"""
    logger.info("=" * 80)
    logger.info("TEST 1: Fact Extraction and Action Generation")
    logger.info("=" * 80)
    
    generator = CandidateActionGenerator()
    
    # Test facts
    facts = [
        "RivalCorp is burning cash at $2M/month and has only 8 months of runway left",
        "TechCorp's supply chain relies on a single supplier in Vietnam",
        "A government contract worth $50M is up for bid next quarter",
    ]
    
    # Extract actions
    raw_candidates = generator._extract_actions_from_facts(facts)
    
    logger.info(f"\n✓ Extracted {len(raw_candidates)} raw actions from {len(facts)} facts")
    
    for action_name, source_fact, target in raw_candidates:
        logger.info(f"  - {action_name}")
        logger.info(f"    Source: {source_fact[:60]}...")
        logger.info(f"    Target: {target}")
    
    # Verify we got relevant actions
    assert len(raw_candidates) > 0, "Should extract at least one action"
    
    # Check for expected keywords
    action_names = [a[0] for a in raw_candidates]
    action_text = " ".join(action_names).lower()
    
    assert "rivalcorp" in action_text or "target" in action_text, "Should extract target entity"
    assert any(keyword in action_text for keyword in ["burn", "supply", "contract", "bid"]), \
        "Should extract relevant action keywords"
    
    logger.success("\n✓ TEST 1 PASSED")
    return True


def test_goal_alignment_scoring():
    """Test that actions are scored by goal alignment"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Goal Alignment Scoring")
    logger.info("=" * 80)
    
    generator = CandidateActionGenerator()
    
    # Create mock goal object (without using the Goal model to avoid DB imports)
    class MockGoal:
        def __init__(self):
            self.id = uuid4()
            self.agent_id = uuid4()
            self.description = "Maximize wealth"
            self.goal_type = "wealth"
            self.priority = 0.9
            self.progress = 0.0
            self.knowledge_score = 0.7
            self.status = "active"
            self.created_at = datetime.utcnow()
    
    goal = MockGoal()
    
    # Raw candidates (action_name, source_fact, target)
    raw_candidates = [
        ("bid_on_government_contract", "Government contract available", "government"),
        ("lobby_board_members", "Board is divided", "RivalCorp"),
        ("expose_environmental_violations", "Environmental issues found", "TechCorp"),
    ]
    
    # Score by goal alignment
    scored = generator._score_by_goal_alignment(raw_candidates, goal)
    
    logger.info(f"\n✓ Scored {len(scored)} candidates for wealth goal:")
    for candidate in scored:
        logger.info(f"  - {candidate.display_name}: alignment={candidate.goal_alignment:.2f}")
    
    # Verify scoring
    assert len(scored) == len(raw_candidates), "Should score all candidates"
    
    # Wealth-aligned actions should score higher
    wealth_actions = [c for c in scored if "contract" in c.action_name.lower() or "bid" in c.action_name.lower()]
    if wealth_actions:
        assert wealth_actions[0].goal_alignment >= 0.3, "Wealth-aligned actions should have decent score"
    
    # Verify candidates are sorted by alignment
    for i in range(len(scored) - 1):
        assert scored[i].goal_alignment >= scored[i+1].goal_alignment, \
            "Should be sorted by alignment descending"
    
    logger.success("\n✓ TEST 2 PASSED")
    return True


def test_personality_filtering():
    """Test that personality traits filter actions"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Personality-Based Filtering")
    logger.info("=" * 80)
    
    generator = CandidateActionGenerator()
    
    # Create candidates with various risk levels
    candidates = [
        CandidateAction(
            action_name="sabotage_competitor_operations",
            display_name="Sabotage competitor operations",
            source_fact="Competitor has vulnerabilities",
            goal_alignment=0.8,
            risk_level=0.9,  # High risk
        ),
        CandidateAction(
            action_name="expose_environmental_violations",
            display_name="Expose environmental violations",
            source_fact="Environmental issues found",
            goal_alignment=0.7,
            risk_level=0.3,  # Low risk
        ),
        CandidateAction(
            action_name="exploit_supply_chain_weakness",
            display_name="Exploit supply chain weakness",
            source_fact="Supply chain vulnerable",
            goal_alignment=0.6,
            risk_level=0.6,  # Medium risk
        ),
    ]
    
    # High morality, low risk tolerance personality
    ethical_personality = {
        "morality": 0.9,
        "risk_tolerance": 0.2,
        "empathy": 0.8,
    }
    
    filtered = generator._filter_by_personality(candidates, ethical_personality)
    
    logger.info(f"\n✓ Filtered {len(candidates)} -> {len(filtered)} for ethical personality")
    logger.info("  Remaining actions:")
    for candidate in filtered:
        logger.info(f"    - {candidate.display_name} (risk: {candidate.risk_level:.2f})")
    
    # Verify filtering
    assert len(filtered) < len(candidates), "Should filter out some actions"
    
    # Sabotage should be blocked (high morality)
    sabotage_actions = [c for c in filtered if "sabotage" in c.action_name.lower()]
    assert len(sabotage_actions) == 0, "Should block sabotage for high morality"
    
    # Exploit should be blocked (high empathy)
    exploit_actions = [c for c in filtered if "exploit" in c.action_name.lower()]
    assert len(exploit_actions) == 0, "Should block exploit for high empathy"
    
    # Expose should remain (ethical action)
    expose_actions = [c for c in filtered if "expose" in c.action_name.lower()]
    assert len(expose_actions) > 0, "Should keep ethical actions"
    
    logger.success("\n✓ TEST 3 PASSED")
    return True


def test_cooldown_blocking():
    """Test that cooldown system blocks repeated actions"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Cooldown Blocking")
    logger.info("=" * 80)
    
    cooldown_mgr = ActionCooldownManager()
    
    # Create recent actions
    recent_actions = [
        RecentAction(
            action_type="exploit_rivalcorp_supply_chain_weakness",
            action_category="business",
            step_number=5,
            success=True,
            outcome="Success",
        ),
        RecentAction(
            action_type="bid_on_government_contract",
            action_category="business",
            step_number=4,
            success=False,  # Failed action
            outcome="Failed",
        ),
    ]
    
    # Create candidates
    candidates = [
        CandidateAction(
            action_name="exploit_rivalcorp_supply_chain_weakness",  # Same as recent
            display_name="Exploit RivalCorp supply chain weakness",
            source_fact="Supply chain vulnerable",
            goal_alignment=0.8,
            risk_level=0.6,
        ),
        CandidateAction(
            action_name="bid_on_government_contract",  # Failed recently
            display_name="Bid on government contract",
            source_fact="Contract available",
            goal_alignment=0.7,
            risk_level=0.3,
        ),
        CandidateAction(
            action_name="launch_new_product",  # Different action
            display_name="Launch new product",
            source_fact="Market opportunity",
            goal_alignment=0.6,
            risk_level=0.4,
        ),
    ]
    
    # Apply cooldowns at step 6 (1 step after most recent action)
    current_step = 6
    filtered = cooldown_mgr.apply_cooldowns(candidates, recent_actions, current_step)
    
    logger.info(f"\n✓ At step {current_step}: {len(candidates)} -> {len(filtered)} candidates")
    logger.info("  Remaining actions:")
    for candidate in filtered:
        logger.info(f"    - {candidate.display_name}")
    
    # Verify exact action is blocked
    exploit_actions = [c for c in filtered if "exploit" in c.action_name.lower() and "rivalcorp" in c.action_name.lower()]
    assert len(exploit_actions) == 0, "Should block exact action within cooldown"
    
    # Verify failed action is blocked
    bid_actions = [c for c in filtered if "bid" in c.action_name.lower()]
    assert len(bid_actions) == 0, "Should block failed action within extended cooldown"
    
    # Verify unrelated action is available
    launch_actions = [c for c in filtered if "launch" in c.action_name.lower()]
    assert len(launch_actions) > 0, "Should keep unrelated actions"
    
    # Test cooldown expiration at step 9
    current_step = 9
    filtered_later = cooldown_mgr.apply_cooldowns(candidates, recent_actions, current_step)
    
    logger.info(f"\n✓ At step {current_step} (cooldown expired): {len(filtered_later)} candidates")
    
    # Exploit should be available again (3-step cooldown expired)
    exploit_actions_later = [c for c in filtered_later if "exploit" in c.action_name.lower()]
    assert len(exploit_actions_later) > 0, "Should allow action after cooldown expires"
    
    # Failed action still blocked (5-step cooldown)
    bid_actions_later = [c for c in filtered_later if "bid" in c.action_name.lower()]
    assert len(bid_actions_later) == 0, "Should still block failed action (longer cooldown)"
    
    logger.success("\n✓ TEST 4 PASSED")
    return True


def test_category_penalty():
    """Test that same-category actions get penalized"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Category Penalty")
    logger.info("=" * 80)
    
    cooldown_mgr = ActionCooldownManager()
    
    # Recent business action
    recent_actions = [
        RecentAction(
            action_type="expand_business_operations",
            action_category="business",
            step_number=5,
            success=True,
            outcome="Success",
        ),
    ]
    
    # Candidates with different categories
    candidates = [
        CandidateAction(
            action_name="launch_new_product",  # Business category
            display_name="Launch new product",
            source_fact="Market opportunity",
            goal_alignment=0.8,
            risk_level=0.4,
        ),
        CandidateAction(
            action_name="organize_press_conference",  # Influence category
            display_name="Organize press conference",
            source_fact="Media interest",
            goal_alignment=0.7,
            risk_level=0.3,
        ),
    ]
    
    # Apply cooldowns at step 6
    current_step = 6
    filtered = cooldown_mgr.apply_cooldowns(candidates, recent_actions, current_step)
    
    logger.info(f"\n✓ Applied category penalties:")
    for candidate in filtered:
        logger.info(
            f"  - {candidate.display_name}: "
            f"alignment={candidate.goal_alignment:.2f}, "
            f"penalty={candidate.cooldown_penalty:.2f}"
        )
    
    # Business action should have penalty
    business_actions = [c for c in filtered if "launch" in c.action_name.lower()]
    if business_actions:
        assert business_actions[0].cooldown_penalty > 0, "Business action should have category penalty"
        assert business_actions[0].goal_alignment < 0.8, "Alignment should be reduced by penalty"
    
    # Non-business action should have no penalty
    influence_actions = [c for c in filtered if "press" in c.action_name.lower()]
    if influence_actions:
        assert influence_actions[0].cooldown_penalty == 0, "Different category should have no penalty"
    
    logger.success("\n✓ TEST 5 PASSED")
    return True


def run_all_tests():
    """Run all unit tests"""
    logger.info("\n" + "=" * 80)
    logger.info("DECISION PIPELINE PHASE 1 - UNIT TEST SUITE")
    logger.info("=" * 80)
    
    tests = [
        ("Fact Extraction", test_fact_extraction),
        ("Goal Alignment Scoring", test_goal_alignment_scoring),
        ("Personality Filtering", test_personality_filtering),
        ("Cooldown Blocking", test_cooldown_blocking),
        ("Category Penalty", test_category_penalty),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            logger.error(f"\n✗ {test_name} FAILED: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"\n✗ {test_name} ERROR: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        logger.success("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error(f"\n❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
