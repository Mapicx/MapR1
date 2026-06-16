"""
MapR1 — World Knowledge System

Implements a layered knowledge model:
  - PUBLIC facts: visible to all agents from the start
  - HIDDEN facts: only revealed through gather_information actions
  - AGENT-SPECIFIC discoveries: stored in agent memory, tracked per goal

When an agent gathers information, this system:
  1. Picks 1-3 hidden facts relevant to the agent's goals and type
  2. Returns specific, named discoveries (not generic "gathered info")
  3. Updates the goal's knowledge_score toward the 0.65 threshold
  4. Once threshold is reached, gather_information is removed from
     available actions for that goal, forcing execution actions
"""

import random
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from loguru import logger

from backend.models.agent_models import Agent


# ── Public world facts (every agent knows these from step 1) ─────────────────

PUBLIC_FACTS: Dict[str, List[str]] = {
    "economy": [
        "The economy is growing at 3.2% annually",
        "Consumer spending is up 8% year-over-year",
        "Interest rates are at a 10-year low",
    ],
    "technology": [
        "AI adoption is accelerating across all industries",
        "Cloud infrastructure costs dropped 20% this year",
        "Cybersecurity incidents are up 40% industry-wide",
    ],
    "politics": [
        "New environmental regulations are being debated in Congress",
        "Corporate tax reform is on the legislative agenda",
        "Public trust in large corporations is at an all-time low",
    ],
    "market": [
        "The tech sector is experiencing consolidation",
        "Venture capital funding is down 30% from peak",
        "Consumer demand for sustainable products is rising",
    ],
}

# ── Hidden facts revealed through information gathering ──────────────────────
# Keyed by (agent_type, goal_type) tuples for relevance matching.
# Each entry is a list of specific, named discoveries.

HIDDEN_FACTS: Dict[Tuple[str, str], List[str]] = {

    # CEO / wealth goals
    ("ceo", "wealth"): [
        "TechCorp's supply chain relies on a single supplier in Vietnam — a critical vulnerability",
        "RivalCorp is burning cash at $2M/month and has only 8 months of runway left",
        "A major retail chain is quietly looking for a new enterprise software vendor",
        "TechCorp's top 3 engineers are actively interviewing at competitors",
        "RivalCorp's flagship product has a known security flaw not yet patched",
        "A government contract worth $50M is up for bid next quarter",
        "TechCorp's patent on their core algorithm expires in 18 months",
        "RivalCorp's CEO has a strained relationship with their board of directors",
    ],

    # CEO / power goals
    ("ceo", "power"): [
        "RivalCorp's board is divided — 3 members want to sell the company",
        "A key RivalCorp investor is unhappy with recent performance",
        "TechCorp controls 28% market share; RivalCorp has 19%",
        "A smaller competitor, NovaTech, is gaining traction in the SMB segment",
        "RivalCorp is planning a hostile acquisition of NovaTech next quarter",
        "The industry regulator is investigating RivalCorp for anti-competitive practices",
        "TechCorp's brand recognition is 2x higher than RivalCorp in enterprise surveys",
    ],

    # Activist / ideology goals
    ("activist", "ideology"): [
        "TechCorp's data center in Nevada has been illegally dumping coolant waste",
        "RivalCorp sources rare earth minerals from a mine with documented labor violations",
        "A whistleblower inside TechCorp has evidence of falsified environmental reports",
        "Environmental lawyers in California are building a class-action case against TechCorp",
        "A coalition of 12 activist groups in the Bay Area is looking for a leader",
        "Three city council members in San Jose are sympathetic to environmental causes",
        "TechCorp's ESG score dropped 15 points last quarter — investors are noticing",
        "A major pension fund is considering divesting from TechCorp over ESG concerns",
        "Local media in Austin is investigating RivalCorp's water usage practices",
    ],

    # Activist / relationships goals
    ("activist", "relationships"): [
        "Greenpeace has an active chapter in San Francisco open to new partnerships",
        "A prominent climate journalist at the NYT is looking for corporate wrongdoing stories",
        "The Sierra Club is organizing a tech industry accountability summit next month",
        "Two university professors are publishing research on tech industry environmental impact",
        "A former TechCorp employee turned activist has 50K social media followers",
    ],

    # Generic fallbacks by goal type
    ("*", "wealth"): [
        "A new market segment worth $200M is emerging in Southeast Asia",
        "Supply chain disruptions are creating pricing opportunities",
        "A competitor's key patent is being challenged in court",
    ],
    ("*", "power"): [
        "A key decision-maker in the industry is looking for new alliances",
        "Regulatory changes will shift power dynamics in 6 months",
        "A competitor's leadership team is in internal conflict",
    ],
    ("*", "ideology"): [
        "Public opinion is shifting toward your cause — 62% support in recent polls",
        "A major media outlet is interested in covering your movement",
        "Corporate opponents are vulnerable to reputational pressure right now",
    ],
    ("*", "knowledge"): [
        "A research paper reveals a critical gap in current industry practices",
        "An insider source can provide access to restricted information",
        "A technical vulnerability has been discovered in a competitor's system",
    ],
    ("*", "*"): [
        "A key player in this space is more vulnerable than they appear",
        "An unexpected alliance opportunity has emerged",
        "Recent events have created a window of opportunity that won't last long",
    ],
}

# ── Knowledge sufficiency thresholds ─────────────────────────────────────────

# Once knowledge_score reaches this value, gather_information is blocked
KNOWLEDGE_THRESHOLD = 0.65

# How much each successful gather adds to knowledge_score
KNOWLEDGE_GAIN_PER_GATHER = 0.25

# How many facts are revealed per successful gather
FACTS_PER_GATHER = random.randint(1, 2)  # evaluated at import, fine for module-level default


class WorldKnowledgeSystem:
    """
    Manages what agents know vs. what is hidden in the world.
    Produces specific discoveries when agents gather information.
    """

    def get_public_situation(self, world_state_dict: Optional[Dict]) -> str:
        """
        Build the public situation description an agent sees.
        Includes world state + public facts — no hidden information.
        """
        parts = []

        if world_state_dict:
            parts.append("=== PUBLIC WORLD STATE ===")
            for k, v in list(world_state_dict.items())[:8]:
                parts.append(f"  {k}: {v}")

        parts.append("\n=== PUBLIC KNOWLEDGE ===")
        for category, facts in PUBLIC_FACTS.items():
            parts.append(f"  [{category.upper()}]")
            for fact in facts[:2]:  # Only show 2 per category to keep prompt lean
                parts.append(f"    - {fact}")

        return "\n".join(parts)

    def gather_information(
        self,
        agent: Agent,
        goal_type: str,
        existing_discoveries: List[str],
    ) -> Tuple[List[str], float, str]:
        """
        Simulate an information-gathering action.

        Returns:
            (new_discoveries, knowledge_gain, narrative_outcome)
            - new_discoveries: list of specific facts discovered
            - knowledge_gain: how much to add to knowledge_score (0.0-0.35)
            - narrative_outcome: human-readable outcome string
        """
        agent_type = agent.agent_type.lower()
        goal_type_lower = goal_type.lower()

        # Build candidate pool: specific match > agent wildcard > goal wildcard > generic
        candidates: List[str] = []

        specific_key = (agent_type, goal_type_lower)
        if specific_key in HIDDEN_FACTS:
            candidates.extend(HIDDEN_FACTS[specific_key])

        agent_wildcard = ("*", goal_type_lower)
        if agent_wildcard in HIDDEN_FACTS:
            candidates.extend(HIDDEN_FACTS[agent_wildcard])

        goal_wildcard = (agent_type, "*")
        if goal_wildcard in HIDDEN_FACTS:
            candidates.extend(HIDDEN_FACTS[goal_wildcard])

        candidates.extend(HIDDEN_FACTS[("*", "*")])

        # Remove already-discovered facts
        fresh = [f for f in candidates if f not in existing_discoveries]

        if not fresh:
            # Nothing new to discover
            return (
                [],
                0.05,  # tiny gain for trying
                f"{agent.name} searched for new information but found nothing they didn't already know.",
            )

        # Pick 1-2 fresh facts
        count = min(random.randint(1, 2), len(fresh))
        discovered = random.sample(fresh, count)

        # Knowledge gain: more facts = more gain, with some randomness
        gain = round(KNOWLEDGE_GAIN_PER_GATHER * count * random.uniform(0.8, 1.2), 3)
        gain = min(gain, 0.35)  # cap per gather

        # Build narrative
        if len(discovered) == 1:
            narrative = f"{agent.name} discovered: {discovered[0]}"
        else:
            items = "; ".join(discovered)
            narrative = f"{agent.name} uncovered {len(discovered)} key facts: {items}"

        logger.info(f"[WorldKnowledge] {agent.name} discovered {len(discovered)} facts (gain: +{gain:.2f})")
        return discovered, gain, narrative

    def should_block_gather_information(self, knowledge_score: float) -> bool:
        """Return True if the agent has gathered enough info and should move to action."""
        return knowledge_score >= KNOWLEDGE_THRESHOLD

    def get_execution_actions_for_goal(
        self, agent_type: str, goal_type: str
    ) -> List[str]:
        """
        Return execution-phase actions appropriate for this agent/goal combo.
        These replace gather_information once the threshold is reached.
        """
        execution_map: Dict[Tuple[str, str], List[str]] = {
            ("ceo", "wealth"): [
                "exploit competitor supply chain weakness",
                "poach competitor's key engineers",
                "bid on government contract",
                "launch targeted product to steal market share",
                "acquire struggling competitor",
            ],
            ("ceo", "power"): [
                "lobby board members of rival company",
                "launch hostile acquisition of NovaTech",
                "file regulatory complaint against competitor",
                "form strategic partnership to dominate market",
                "pressure competitor's investors",
            ],
            ("activist", "ideology"): [
                "expose TechCorp environmental violations to media",
                "organize protest at TechCorp headquarters",
                "file formal complaint with environmental regulator",
                "coordinate with activist coalition",
                "brief sympathetic city council members",
                "connect whistleblower with investigative journalist",
            ],
            ("activist", "relationships"): [
                "partner with Greenpeace chapter",
                "brief NYT journalist on corporate wrongdoing",
                "speak at Sierra Club summit",
                "collaborate with university researchers",
                "amplify former employee activist's platform",
            ],
        }

        # Try specific match first, then agent wildcard, then generic
        key = (agent_type.lower(), goal_type.lower())
        if key in execution_map:
            return execution_map[key]

        # Generic execution actions by goal type
        generic: Dict[str, List[str]] = {
            "wealth": ["exploit market opportunity", "undercut competitor pricing", "secure major contract"],
            "power": ["consolidate influence", "neutralize opposition", "form dominant coalition"],
            "ideology": ["launch public campaign", "pressure key decision-makers", "build movement momentum"],
            "knowledge": ["publish findings", "exploit discovered vulnerability", "share intelligence with allies"],
            "relationships": ["formalize alliance", "host coalition meeting", "broker key introduction"],
        }
        return generic.get(goal_type.lower(), ["take decisive action", "execute on gathered intelligence"])


    def register_scenario_facts(
        self,
        project_id: UUID,
        facts: List,  # List[HiddenFactSeed] but avoiding circular import
    ):
        """
        Register scenario-specific hidden facts for a project.
        
        These are stored in memory and merged with the static HIDDEN_FACTS
        during gather_information().
        
        Args:
            project_id: Project UUID
            facts: List of HiddenFactSeed objects from scenario seeder
        """
        if not hasattr(self, "_scenario_facts"):
            self._scenario_facts: Dict[UUID, List] = {}
        
        self._scenario_facts[project_id] = facts
        logger.info(
            f"Registered {len(facts)} scenario-specific hidden facts for project {project_id}"
        )
    
    def get_scenario_facts(self, project_id: UUID) -> List:
        """Get scenario-specific facts for a project."""
        if not hasattr(self, "_scenario_facts"):
            return []
        return self._scenario_facts.get(project_id, [])


# Module-level singleton
world_knowledge_system = WorldKnowledgeSystem()

# Keep old name for backward compatibility
world_knowledge = world_knowledge_system
