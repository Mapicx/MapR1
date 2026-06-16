"""
MapR1 — Context-Aware Candidate Action Generator

Generates context-aware candidate actions based on:
- Agent's discovered facts (from memory_type='discovery')
- Agent's active goals
- Agent's relationships (allies, enemies)
- Current world state
- Agent's personality and type

Replaces static action lists with dynamically generated, fact-driven actions.
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.agent_models import Agent
from backend.models.goal_models import Goal as AgentGoal
from backend.models.relationship_models import AgentRelationship
from backend.models.world_models import WorldState
from backend.models.action_models import CandidateAction


# ── Pattern-Based Fact-to-Action Mapping ────────────────────────────────────
# Maps regex patterns in discovered facts to action templates
# {target} placeholder is replaced with entity names extracted from facts

FACT_ACTION_PATTERNS: Dict[str, List[str]] = {
    # Supply chain vulnerabilities
    r"supply.?chain.*(weakness|vulnerability|single supplier|relies on)": [
        "exploit_{target}_supply_chain_weakness",
        "secure_alternative_vendor_to_undercut_{target}",
        "approach_{target}_supplier_for_exclusive_deal",
    ],
    
    # Cash/runway problems
    r"(burning cash|runway|cash.?flow|financial.?trouble)": [
        "undercut_{target}_pricing_to_accelerate_burn",
        "poach_{target}_key_employees_during_instability",
        "acquire_{target}_before_bankruptcy",
    ],
    
    # Whistleblower / evidence
    r"(whistleblower|evidence|falsified|illegal|violations)": [
        "coordinate_media_leak_about_{target}",
        "connect_whistleblower_with_journalist",
        "build_legal_case_against_{target}",
        "file_regulatory_complaint_about_{target}",
    ],
    
    # Media interest
    r"(journalist|media|reporter|coverage|NYT|press)": [
        "brief_journalist_on_{target}_wrongdoing",
        "organize_press_conference",
        "launch_viral_social_media_campaign",
    ],
    
    # Investor/board dissent
    r"(board.*(divided|conflict)|investor.*(unhappy|divesting))": [
        "lobby_{target}_dissident_board_members",
        "approach_{target}_unhappy_investors",
        "propose_hostile_takeover_of_{target}",
    ],
    
    # Coalition / allies available
    r"(coalition|chapter|summit|movement|looking for.*(leader|partner))": [
        "join_{target}_coalition_as_leader",
        "organize_joint_action_with_allies",
        "host_strategy_meeting_with_coalition",
    ],
    
    # Key talent vulnerable
    r"(engineer|talent|employee).*(interviewing|leaving|poach|recruit)": [
        "recruit_{target}_key_engineers",
        "offer_retention_packages_to_own_talent",
    ],
    
    # Government/contract opportunity
    r"(government.?contract|bid|regulatory|regulator)": [
        "bid_on_government_contract",
        "file_regulatory_complaint_against_{target}",
        "lobby_regulator_for_favorable_ruling",
    ],
    
    # Patent/IP vulnerability
    r"(patent|intellectual property|IP).*(expir|vulnerab|challeng)": [
        "challenge_{target}_patent_in_court",
        "develop_alternative_to_{target}_patented_technology",
        "acquire_{target}_before_patent_expires",
    ],
    
    # Market opportunity
    r"(market.*(segment|opportunity)|demand.*(rising|growing))": [
        "launch_product_targeting_new_market_segment",
        "expand_operations_into_emerging_market",
    ],
    
    # Environmental/ESG issues
    r"(environmental|ESG|dumping|pollution|labor.?violations)": [
        "expose_{target}_environmental_violations_to_media",
        "file_formal_complaint_with_environmental_regulator",
        "organize_protest_at_{target}_headquarters",
        "pressure_{target}_investors_over_ESG_concerns",
    ],
    
    # Research/academic connections
    r"(research|professor|university|study)": [
        "collaborate_with_university_researchers",
        "publish_research_findings",
        "leverage_academic_credibility",
    ],
    
    # Social media / influencer
    r"(social.?media|followers|viral|influencer)": [
        "amplify_{target}_activist_platform",
        "launch_viral_social_media_campaign",
        "coordinate_online_movement",
    ],
}


# ── Goal-Action Affinity Keywords ───────────────────────────────────────────
# Keywords that indicate an action aligns with a goal type

GOAL_ACTION_AFFINITY: Dict[str, List[str]] = {
    "wealth": ["exploit", "acquire", "undercut", "bid", "contract", "pricing", "vendor", "market"],
    "power": ["lobby", "takeover", "acquire", "coalition", "board", "investor", "hostile", "dominance"],
    "ideology": ["media", "campaign", "leak", "legal_case", "regulatory", "protest", "whistleblower", "expose"],
    "relationships": ["join", "coalition", "ally", "partner", "recruit", "host", "collaborate"],
    "knowledge": ["investigate", "research", "intelligence", "infiltrate", "gather", "study"],
    "influence": ["media", "campaign", "viral", "pressure", "lobby", "organize"],
    "reputation": ["media", "campaign", "expose", "publish", "credibility"],
}


# ── Personality-Based Action Filters ────────────────────────────────────────
# Actions that should be blocked based on personality traits

# High morality (>0.7) agents should NOT see these actions
MORALITY_BLOCKED = ["sabotage", "leak", "betray", "exploit_weakness", "illegal"]

# Low risk_tolerance (<0.3) agents should NOT see these actions
RISK_BLOCKED = ["hostile_takeover", "sabotage", "attack", "illegal", "infiltrate"]

# High empathy (>0.7) agents should NOT see these actions
EMPATHY_BLOCKED = ["undercut", "poach", "exploit", "attack", "aggressive"]


class CandidateActionGenerator:
    """
    Generates context-aware candidate actions based on discovered facts,
    goals, relationships, and personality.
    """

    async def generate_candidates(
        self,
        db: AsyncSession,
        agent: Agent,
        discovered_facts: List[str],
        active_goals: List[AgentGoal],
        relationships: List[AgentRelationship],
        world_state: Optional[WorldState],
        recently_attempted: List[str],
    ) -> List[CandidateAction]:
        """
        Generate a ranked list of 5-8 context-aware candidate actions.
        
        Process:
        1. Extract actions from discovered facts using pattern matching
        2. Filter by goal alignment
        3. Filter by personality constraints
        4. Rank by goal alignment score
        5. Return top 5-8 candidates
        
        Args:
            db: Database session
            agent: The agent making the decision
            discovered_facts: Facts the agent has discovered
            active_goals: Agent's active goals
            relationships: Agent's relationships
            world_state: Current world state
            recently_attempted: Recently attempted action names (for filtering)
            
        Returns:
            List of CandidateAction objects, ranked by goal alignment
        """
        logger.info(f"Generating candidates for {agent.name} from {len(discovered_facts)} facts")
        
        # Step 1: Extract actions from facts
        raw_candidates = self._extract_actions_from_facts(discovered_facts)
        logger.debug(f"Extracted {len(raw_candidates)} raw candidates from facts")
        
        # Step 2: Score by goal alignment
        primary_goal = active_goals[0] if active_goals else None
        scored_candidates = self._score_by_goal_alignment(
            raw_candidates, 
            primary_goal
        )
        
        # Step 3: Filter by personality
        filtered_candidates = self._filter_by_personality(
            scored_candidates,
            agent.personality
        )
        logger.debug(f"After personality filter: {len(filtered_candidates)} candidates")
        
        # Step 4: Remove recently attempted actions
        filtered_candidates = [
            c for c in filtered_candidates 
            if c.action_name not in recently_attempted
        ]
        
        # Step 5: Sort by goal alignment (descending) and take top 8
        filtered_candidates.sort(key=lambda c: c.goal_alignment, reverse=True)
        top_candidates = filtered_candidates[:8]
        
        logger.info(
            f"Generated {len(top_candidates)} candidates for {agent.name} "
            f"(avg alignment: {sum(c.goal_alignment for c in top_candidates) / len(top_candidates):.2f})"
            if top_candidates else f"Generated 0 candidates for {agent.name}"
        )
        
        return top_candidates

    # ── Private Methods ─────────────────────────────────────────────────────

    def _extract_actions_from_facts(
        self, 
        discovered_facts: List[str]
    ) -> List[Tuple[str, str, str]]:
        """
        Extract actions from discovered facts using pattern matching.
        
        Returns:
            List of (action_template, source_fact, target_entity) tuples
        """
        candidates = []
        
        for fact in discovered_facts:
            # Try each pattern
            for pattern, action_templates in FACT_ACTION_PATTERNS.items():
                if re.search(pattern, fact, re.IGNORECASE):
                    # Extract target entity from fact
                    target = self._extract_target_entity(fact)
                    
                    # Generate actions from templates
                    for template in action_templates:
                        action_name = template.replace("{target}", target)
                        candidates.append((action_name, fact, target))
        
        return candidates

    def _extract_target_entity(self, fact: str) -> str:
        """
        Extract entity name from a fact string.
        
        Looks for capitalized words that might be company/entity names.
        Falls back to "target" if no entity found.
        """
        # Common entity patterns: TechCorp, RivalCorp, NovaTech, etc.
        # Look for capitalized words (but not at start of sentence)
        words = fact.split()
        
        for i, word in enumerate(words):
            # Skip first word (might be capitalized as sentence start)
            if i == 0:
                continue
            
            # Look for capitalized words that might be entity names
            if word[0].isupper() and len(word) > 3:
                # Check if it looks like a company name
                if any(suffix in word for suffix in ["Corp", "Tech", "Inc", "Ltd", "Co"]):
                    return word.replace("'s", "").replace(",", "").replace(".", "")
                
                # Check if next word is also capitalized (multi-word entity)
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    return f"{word}_{words[i + 1]}".replace("'s", "")
        
        # Fallback: look for any capitalized word
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and len(word) > 3:
                return word.replace("'s", "").replace(",", "").replace(".", "")
        
        return "target"

    def _score_by_goal_alignment(
        self,
        raw_candidates: List[Tuple[str, str, str]],
        primary_goal: Optional[AgentGoal],
    ) -> List[CandidateAction]:
        """
        Score candidates by alignment with primary goal.
        
        Uses keyword matching between action name and goal affinity keywords.
        """
        scored = []
        
        goal_type = primary_goal.goal_type if primary_goal else "wealth"
        affinity_keywords = GOAL_ACTION_AFFINITY.get(goal_type, [])
        
        for action_name, source_fact, target in raw_candidates:
            # Count keyword matches
            action_lower = action_name.lower()
            matches = sum(1 for keyword in affinity_keywords if keyword in action_lower)
            
            # Calculate alignment score (0-1)
            # Base score of 0.3, +0.1 per keyword match, capped at 1.0
            alignment = min(1.0, 0.3 + (matches * 0.15))
            
            # Estimate risk level based on action keywords
            risk = self._estimate_risk_level(action_name)
            
            # Create display name (human-readable)
            display_name = self._create_display_name(action_name)
            
            scored.append(CandidateAction(
                action_name=action_name,
                display_name=display_name,
                source_fact=source_fact,
                goal_alignment=alignment,
                risk_level=risk,
                cooldown_penalty=0.0,
            ))
        
        return scored

    def _estimate_risk_level(self, action_name: str) -> float:
        """
        Estimate risk level of an action based on keywords.
        
        Returns:
            Risk score 0.0-1.0 (0 = safe, 1 = very risky)
        """
        action_lower = action_name.lower()
        
        # High risk keywords
        high_risk = ["hostile", "sabotage", "attack", "illegal", "infiltrate", "exploit"]
        medium_risk = ["acquire", "takeover", "poach", "undercut", "aggressive"]
        low_risk = ["gather_intel", "research", "collaborate", "partner", "join"]
        
        if any(keyword in action_lower for keyword in high_risk):
            return 0.8
        elif any(keyword in action_lower for keyword in medium_risk):
            return 0.5
        elif any(keyword in action_lower for keyword in low_risk):
            return 0.2
        else:
            return 0.4  # Default medium-low risk

    def _create_display_name(self, action_name: str) -> str:
        """
        Convert action_name to human-readable display name.
        
        Example: "exploit_rivalcorp_supply_chain_weakness" 
                 -> "Exploit RivalCorp supply chain weakness"
        """
        # Replace underscores with spaces
        display = action_name.replace("_", " ")
        
        # Capitalize first letter
        display = display[0].upper() + display[1:] if display else display
        
        # Capitalize entity names (words that look like proper nouns)
        words = display.split()
        for i, word in enumerate(words):
            # Capitalize if it looks like an entity name
            if any(suffix in word.lower() for suffix in ["corp", "tech", "inc", "ltd"]):
                words[i] = word.capitalize()
        
        return " ".join(words)

    def _filter_by_personality(
        self,
        candidates: List[CandidateAction],
        personality: Dict,
    ) -> List[CandidateAction]:
        """
        Filter out actions that don't fit the agent's personality.
        
        Rules:
        - High morality (>0.7): block unethical actions
        - Low risk tolerance (<0.3): block risky actions
        - High empathy (>0.7): block harmful actions
        """
        morality = personality.get("morality", 0.5)
        risk_tolerance = personality.get("risk_tolerance", 0.5)
        empathy = personality.get("empathy", 0.5)
        
        filtered = []
        
        for candidate in candidates:
            action_lower = candidate.action_name.lower()
            
            # Check morality blocks
            if morality > 0.7:
                if any(blocked in action_lower for blocked in MORALITY_BLOCKED):
                    logger.debug(
                        f"Blocking '{candidate.display_name}' - violates high morality"
                    )
                    continue
            
            # Check risk tolerance blocks
            if risk_tolerance < 0.3:
                if any(blocked in action_lower for blocked in RISK_BLOCKED):
                    logger.debug(
                        f"Blocking '{candidate.display_name}' - too risky for low risk tolerance"
                    )
                    continue
            
            # Check empathy blocks
            if empathy > 0.7:
                if any(blocked in action_lower for blocked in EMPATHY_BLOCKED):
                    logger.debug(
                        f"Blocking '{candidate.display_name}' - violates high empathy"
                    )
                    continue
            
            # Also filter by risk level vs risk tolerance
            if candidate.risk_level > risk_tolerance + 0.3:
                logger.debug(
                    f"Blocking '{candidate.display_name}' - risk {candidate.risk_level:.2f} "
                    f"exceeds tolerance {risk_tolerance:.2f}"
                )
                continue
            
            filtered.append(candidate)
        
        return filtered
