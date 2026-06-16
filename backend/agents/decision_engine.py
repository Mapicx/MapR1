"""
Decision Engine

LLM-powered decision-making for agents.
Agents use their memory, goals, relationships, and discovered knowledge
to make intelligent decisions.

Key behaviour:
- Agents start with only PUBLIC world facts
- gather_information is available until knowledge_score >= 0.65 for a goal
- Once threshold is reached, execution actions replace gather_information
- Discovered facts are injected into the situation context
"""

from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from pydantic import BaseModel, Field

from backend.models.action_models import AgentAction, AgentDecision, ActionType, CandidateAction
from backend.models.agent_models import Agent, AgentMemory
from backend.agents.agent_memory import AgentMemoryManager
from backend.agents.goal_system import GoalManager
from backend.agents.relationship_system import RelationshipManager
from backend.agents.world_knowledge import world_knowledge, KNOWLEDGE_THRESHOLD
from backend.agents.candidate_generator import CandidateActionGenerator
from backend.agents.action_cooldown import ActionCooldownManager
from backend.models.llm_client import llm_client


class DecisionEngine:
    """LLM-powered decision-making for agents"""

    def __init__(self):
        self.llm = llm_client

    async def make_decision(
        self,
        db: AsyncSession,
        agent: Agent,
        situation: str,
        available_actions: List[str],
        current_step: int = 0,  # NEW: for cooldown tracking
        world_state: Optional[Any] = None,  # NEW: for candidate generation
        theme_resolver: Optional[Any] = None, # NEW: for prompt resolution
        current_allies: Optional[List[Tuple[str, float]]] = None,
    ) -> AgentDecision:
        """
        Make a decision using LLM reasoning.

        Process:
        1. Load goals and check knowledge_score per goal
        2. Load recent actions for cooldown tracking
        3. Generate context-aware candidates (if in execution phase)
        4. Apply cooldown penalties
        5. Filter available actions based on knowledge sufficiency
        6. Inject discovered facts into situation context
        7. Ask LLM to reason and choose
        8. Store decision as memory
        """
        logger.info(f"Agent {agent.name} making decision...")

        memory_manager = AgentMemoryManager(agent.id)
        goal_manager = GoalManager(agent.id)
        rel_manager = RelationshipManager(agent.id)

        # Load goals and their knowledge scores
        active_goals = await goal_manager.get_active_goals(db, limit=5)

        # Determine if gather_information should be blocked
        # Block it if ALL active goals have reached the knowledge threshold
        total_steps = 10
        if world_state and hasattr(world_state, 'state') and isinstance(world_state.state, dict):
            total_steps = world_state.state.get("metadata", {}).get("suggested_steps", 10)

        # Determine if gather_information should be blocked
        # Block it if ALL active goals have reached the knowledge threshold
        def is_goal_ready(g) -> bool:
            ks = g.knowledge_score or 0.0
            if ks >= KNOWLEDGE_THRESHOLD:
                return True
            if current_step >= 3 and ks >= 0.45 and total_steps <= 10:
                return True
            return False

        all_goals_ready = (
            len(active_goals) > 0
            and all(is_goal_ready(g) for g in active_goals)
        )

        # Get the primary goal (highest priority) for action filtering
        primary_goal = active_goals[0] if active_goals else None
        primary_goal_ready = primary_goal is not None and is_goal_ready(primary_goal)

        # NEW: Load recent actions for cooldown
        cooldown_mgr = ActionCooldownManager()
        recent_actions = await cooldown_mgr.get_recent_actions(db, agent.id, lookback_steps=5)

        # Load discovered facts from memory (type="discovery")
        discovered_facts = await self._load_discoveries(db, agent.id)

        # NEW: Fetch known facts for intel sharing
        from backend.systems.trust_system import TrustMisinformationSystem
        trust_system = TrustMisinformationSystem()
        agent_beliefs = await trust_system._get_or_create_agent_state(db, agent.id)
        known_facts = agent_beliefs.known_facts if agent_beliefs else []

        # NEW: Generate context-aware candidates if in execution phase
        candidates: List[CandidateAction] = []
        if primary_goal_ready and discovered_facts:
            candidate_gen = CandidateActionGenerator()
            relationships = await rel_manager.get_all_relationships(db)
            
            candidates = await candidate_gen.generate_candidates(
                db=db,
                agent=agent,
                discovered_facts=discovered_facts,
                active_goals=active_goals,
                relationships=relationships,
                world_state=world_state,
                recently_attempted=[a.action_type for a in recent_actions],
            )
            
            # Apply cooldowns
            if candidates:
                candidates = cooldown_mgr.apply_cooldowns(
                    candidates, recent_actions, current_step
                )

        # Filter available actions and get recommended strategies
        filtered_actions, strategies = self._filter_actions(
            available_actions=available_actions,
            agent=agent,
            primary_goal=primary_goal,
            primary_goal_ready=primary_goal_ready,
            candidates=candidates,
        )

        # Build enriched situation with public facts + personal discoveries
        enriched_situation = self._build_enriched_situation(
            base_situation=situation,
            discovered_facts=discovered_facts,
            primary_goal=primary_goal,
        )

        # Build remaining context
        memory_context = await memory_manager.build_context(
            db, situation, include_recent=3, include_important=3, include_similar=3
        )
        goal_context = await goal_manager.get_goal_context(db, limit=5)
        relationship_context = await rel_manager.get_relationship_context(db, limit=5)

        # Extract pending proposals directed at this agent
        pending_proposals = []
        if world_state:
            all_proposals = world_state.state.get("pending_proposals", [])
            pending_proposals = [p for p in all_proposals if p.get("to_agent_id") == str(agent.id)]
            
        # Build decision prompt
        prompt = self._build_decision_prompt(
            agent=agent,
            situation=enriched_situation,
            available_actions=filtered_actions,
            memory_context=memory_context,
            goal_context=goal_context,
            relationship_context=relationship_context,
            primary_goal_ready=primary_goal_ready,
            candidates=candidates,
            pending_proposals=pending_proposals,
            strategies=strategies,
            theme_resolver=theme_resolver,
            current_allies=current_allies,
            known_facts=known_facts,
        )

        logger.debug(f"Decision prompt: {len(prompt)} chars, {len(filtered_actions)} actions available")

        from pydantic import ValidationError

        try:
            decision = await self.llm.generate_structured(
                prompt=prompt,
                response_model=AgentDecision,
            )

            logger.info(
                f"Agent {agent.name} decided: {decision.action.value} "
                f"(confidence: {decision.confidence:.2f})"
            )

            # Store decision as memory
            await memory_manager.remember(
                db,
                memory_type="decision",
                content=f"Decided to: {decision.action.value}. Reasoning: {decision.reasoning}",
                importance=0.7,
                emotional_valence=decision.confidence - 0.5,
            )

            return decision

        except ValidationError as e:
            # Check if validation failed specifically on the 'action' field
            if any(err.get('loc') == ('action',) for err in e.errors()):
                logger.warning(f"LLM produced invalid action type enum. Falling back to GATHER_INTEL. Error: {e}")
                return AgentDecision(
                    action=ActionType.GATHER_INTEL,
                    reasoning="Failed to produce a valid enum action. Falling back to gathering intel.",
                    confidence=0.5,
                    expected_outcome="Gain more intelligence safely.",
                    intel_shares=[]
                )
            # Otherwise, re-raise or handle as generic failure
            logger.error(f"Validation failed for {agent.name} decision: {e}")
            return AgentDecision(
                action=ActionType.WAIT,
                reasoning="Validation error on non-action fields. Choosing safe default.",
                confidence=0.3,
                expected_outcome="Stay safe.",
                intel_shares=[]
            )
        except Exception as e:
            logger.error(f"Failed to generate decision for {agent.name}: {e}")
            return AgentDecision(
                action=ActionType.WAIT,
                reasoning="Unable to make informed decision due to generic error.",
                confidence=0.3,
                expected_outcome="Stay safe.",
                intel_shares=[]
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _filter_actions(
        self,
        available_actions: List[str],
        agent: Agent,
        primary_goal: Any,
        primary_goal_ready: bool,
        candidates: Optional[List[CandidateAction]] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Return (filtered_actions, recommended_strategies).
        filtered_actions ALWAYS contains valid ActionType enums.
        """
        if not primary_goal_ready:
            # Still in intel phase — keep gather_information, keep base actions
            return available_actions, []

        # Execution phase — remove gather_information
        filtered = [a for a in available_actions if "gather" not in a.lower()]
        
        # Get recommended strategies to guide the LLM's enum selection
        strategies = []
        if candidates:
            # Use context-aware candidates
            strategies = [c.display_name for c in candidates]
            logger.info(f"Using {len(strategies)} context-aware candidate actions as strategies")
        else:
            # Fallback to old static method
            strategies = world_knowledge.get_execution_actions_for_goal(
                agent_type=agent.agent_type,
                goal_type=primary_goal.goal_type if primary_goal else "wealth",
            )
            logger.debug("Using fallback static execution strategies")

        return filtered, strategies

    async def _load_discoveries(
        self, db: AsyncSession, agent_id: UUID
    ) -> List[str]:
        """Load all facts this agent has previously discovered (memory_type='discovery')."""
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == agent_id,
                AgentMemory.memory_type == "discovery",
            )
            .order_by(AgentMemory.occurred_at.desc())
            .limit(20)
        )
        memories = list(result.scalars().all())
        return [m.content for m in memories]

    def _build_enriched_situation(
        self,
        base_situation: str,
        discovered_facts: List[str],
        primary_goal: Any,
    ) -> str:
        """Combine base situation with agent's personal discoveries."""
        parts = [base_situation]

        if discovered_facts:
            parts.append("\n=== INTELLIGENCE YOU HAVE GATHERED ===")
            for fact in discovered_facts[:10]:  # cap to avoid token overflow
                parts.append(f"  * {fact}")

        if primary_goal:
            ks = primary_goal.knowledge_score or 0.0
            if ks >= KNOWLEDGE_THRESHOLD:
                parts.append(
                    f"\n[You have gathered sufficient intelligence ({ks:.0%}) "
                    f"on your goal '{primary_goal.description[:60]}'. "
                    f"It is time to ACT on what you know, not gather more information.]"
                )
            else:
                parts.append(
                    f"\n[Intelligence sufficiency for your primary goal: {ks:.0%} "
                    f"(target: 65%). Continue gathering information to reach the threshold.]"
                )

        return "\n".join(parts)

    def _build_decision_prompt(
        self,
        agent: Agent,
        situation: str,
        available_actions: List[str],
        memory_context: str,
        goal_context: str,
        relationship_context: str,
        primary_goal_ready: bool,
        candidates: List[CandidateAction] = None,
        pending_proposals: List[Dict] = None,
        strategies: List[str] = None,
        theme_resolver: Optional[Any] = None,
        current_allies: Optional[List[Tuple[str, float]]] = None,
        known_facts: List[Any] = None,
    ) -> str:
        """Build comprehensive decision prompt for LLM."""
        # Resolve the agent role and goal if a theme resolver is provided
        resolved_role = theme_resolver.resolve_role(agent.agent_type) if theme_resolver else agent.agent_type
        personality_desc = self._describe_personality(agent.personality)
        
        # Build compact mutable psychology block
        psych = agent.mutable_psychology or {}
        psych_text = ""
        if psych:
            psych_lines = [
                "YOUR CURRENT MENTAL STATE:",
                f"- Fear: {psych.get('fear', 0.2):.2f}",
                f"- Paranoia: {psych.get('paranoia', 0.3):.2f}",
                f"- Radicalization: {psych.get('radicalization', 0.1):.2f}",
                f"- Desperation: {psych.get('desperation', 0.0):.2f}",
                f"- Ego: {psych.get('ego', 0.5):.2f}",
                f"- Greed: {psych.get('greed', 0.5):.2f}",
                f"- Idealism: {psych.get('idealism', 0.5):.2f}",
                f"- Betrayal Wounds: {psych.get('betrayal_wounds', 0)}"
            ]
            psych_text = "\n".join(psych_lines) + "\n"

        phase_instruction = (
            "You have gathered enough intelligence. Choose an EXECUTION action — "
            "use what you know to make a decisive move toward your goal. "
            "Select the standard action type from the list below that best matches your plan, "
            "and detail your specific target in your `reasoning` and `expected_outcome`."
            if primary_goal_ready
            else "You are still in the intelligence-gathering phase. "
            "Prioritize gathering information to understand the situation before acting."
        )

        # Standard action list (strictly ActionType enum values)
        actions_text = "\n".join(f"{i+1}. {action}" for i, action in enumerate(available_actions))
        actions_text += "\n\nIMPORTANT: These strings must exactly match ActionType enum values. Never paraphrase them."
        
        # Add strategies section if available
        strategies_text = ""
        if strategies:
            strat_lines = ["\nRECOMMENDED STRATEGIES BASED ON INTELLIGENCE:"]
            if candidates and len(candidates) == len(strategies):
                for candidate in candidates:
                    strat_lines.append(
                        f"- {candidate.display_name}\n"
                        f"  (Based on: {candidate.source_fact[:80]}...)"
                    )
            else:
                for strat in strategies:
                    strat_lines.append(f"- {strat}")
            strat_lines.append("\nNote: Use these strategies as inspiration. You MUST select your final action from the exact 'AVAILABLE ACTIONS' list below, and describe your strategy in the `reasoning` field.")
            strategies_text = "\n".join(strat_lines)

        # Format pending proposals
        proposals_text = ""
        if pending_proposals:
            prop_lines = ["\nPENDING PROPOSALS:\nYou have received the following relationship/alliance proposals from other agents:"]
            for p in pending_proposals:
                prop_lines.append(f"- [ID: {p.get('id')}] Proposal type: {p.get('type')} | From: {p.get('from_agent_name')} | Context: \"{p.get('context')}\"")
            prop_lines.append("\nYou MUST evaluate these proposals. In your structured response, map each proposal ID to either 'accept' or 'reject' in the `proposal_responses` dictionary.\nThis is IN ADDITION to your main action.")
            proposals_text = "\n".join(prop_lines)
            
        # Format current allies explicitly for intel sharing / proposal guidance
        allies_text = ""
        if current_allies:
            allies_str = ", ".join([f"{name} (trust: {trust:.1f})" for name, trust in current_allies])
            allies_text = (
                f"\n[CRITICAL]: You have active alliances with the following agents: {allies_str}. "
                f"You MUST NOT propose new alliances to them, and you should consider sharing intel or cooperating with them.\n"
            )
            
        # Format known facts for intel sharing
        facts_text = ""
        if known_facts:
            # Sort by confidence descending, take top 3
            sorted_facts = sorted(known_facts, key=lambda f: getattr(f, 'confidence', 0.0), reverse=True)[:3]
            fact_lines = ["\nYOUR TOP KNOWN FACTS (for intel sharing):"]
            for f in sorted_facts:
                fact_lines.append(f"- \"{getattr(f, 'fact_content', str(f))}\" (Confidence: {getattr(f, 'confidence', 0.0):.2f})")
            facts_text = "\n".join(fact_lines) + "\n"
            
        prompt = f"""You are {agent.name}, a {resolved_role} with the role: {agent.role}.

PERSONALITY:
{personality_desc}

{psych_text}
CURRENT SITUATION:
{situation}

{memory_context}

{goal_context}

{relationship_context}
{strategies_text}
{proposals_text}
{allies_text}
{facts_text}
PHASE GUIDANCE:
{phase_instruction}

AVAILABLE ACTIONS:
You MUST choose EXACTLY ONE of the following action strings. Do not invent new actions.
{actions_text}

Based on your personality, memories, goals, discovered intelligence, and relationships, what should you do?

Think step by step:
1. What intelligence have you already gathered?
2. Which of your goals does this situation affect most?
3. Are you in the intel phase or execution phase?
4. What action best fits your current phase and goals?
5. What are the risks and benefits?

Choose ONE action from the list above and explain your reasoning.

SIDE CHANNEL:
You may simultaneously propose alliances/relationships to other agents using the `outgoing_proposals` field.
You may share intel with your allies using intel_shares. You can share real facts to build trust, or fabricate intel to manipulate them. Consider your allies' goals — misleading them may serve you better than helping them. If you have no allies or nothing worth sharing, leave intel_shares empty.

MACHIAVELLIAN CONSTRAINTS:
1. Alliances: An alliance is an exclusive, major strategic commitment. Aim for a max of ONE or TWO strong alliances. DO NOT ally with everyone.
2. Proposals: Do NOT propose to an agent you are already allied/friends with. If goals conflict, REJECT their proposals.
3. Intel Sharing: You can only share intel with an existing ALLY. 
   - You can share real intel to build trust.
   - You can share fabricated intel (`is_fabricated=true`) to manipulate them.
   - Use `distortion_intent` carefully ("none", "inflate", "deflate", "mislead").
   - `reasoning` is for your internal monologue only; the receiver will NOT see it.
"""
        return prompt

    def _describe_personality(self, personality: dict) -> str:
        """Convert personality traits to natural language description."""
        traits = []

        ambition = personality.get("ambition", 0.5)
        if ambition > 0.8:
            traits.append("extremely ambitious and driven")
        elif ambition > 0.6:
            traits.append("ambitious")
        elif ambition < 0.3:
            traits.append("content with current position")

        risk = personality.get("risk_tolerance", 0.5)
        if risk > 0.7:
            traits.append("bold and risk-taking")
        elif risk < 0.3:
            traits.append("cautious and risk-averse")

        empathy = personality.get("empathy", 0.5)
        if empathy > 0.7:
            traits.append("highly empathetic and caring")
        elif empathy < 0.3:
            traits.append("ruthless and pragmatic")

        rationality = personality.get("rationality", 0.5)
        if rationality > 0.7:
            traits.append("highly rational and analytical")
        elif rationality < 0.3:
            traits.append("emotional and intuitive")

        morality = personality.get("morality", 0.5)
        if morality > 0.7:
            traits.append("principled and ethical")
        elif morality < 0.3:
            traits.append("pragmatic, willing to bend rules")

        creativity = personality.get("creativity", 0.5)
        if creativity > 0.7:
            traits.append("highly creative and innovative")

        if not traits:
            return "You have a balanced personality."
        return "You are " + ", ".join(traits) + "."

    def get_available_actions_for_agent(self, agent: Agent) -> List[str]:
        """Get base actions available to this agent type (before knowledge filtering).
        Aligned with ActionType enum for robust parsing.
        """
        from backend.models.action_models import ActionType
        return [a.value for a in ActionType]
