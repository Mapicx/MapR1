"""
Action Executor

Executes agent actions and calculates their effects on the world.
This is where actions actually happen and change the simulation state.

Action routing uses SemanticActionRouter — LLM output is embedded locally
(~3ms on GPU) and matched to the closest handler via cosine similarity.
No more brittle keyword matching.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, List, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import random

from backend.models.agent_models import Agent
from backend.models.action_models import AgentDecision, ActionExecutionResult, AgentAction
from backend.models.world_models import WorldState, WorldEvent
from backend.agents.agent_memory import AgentMemoryManager
from backend.agents.relationship_system import RelationshipManager
from backend.agents.goal_system import GoalManager
from backend.agents.world_knowledge import world_knowledge
from backend.simulation.action_router import action_router


class ActionExecutor:
    """Executes agent actions and calculates their effects"""
    
    async def execute_action(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: WorldState,
        simulation_step: int,
    ) -> Tuple[ActionExecutionResult, AgentAction]:
        """
        Execute an agent's action and calculate all effects.
        
        This is the core of the simulation - where actions actually happen.
        
        Args:
            agent: Agent performing the action
            decision: The decision made by the agent
            world_state: Current world state
            simulation_step: Current simulation step number
        
        Returns:
            Tuple of (ActionExecutionResult, AgentAction record)
        """
        logger.info(f"Executing action for {agent.name}: {decision.action}")
        
        # Calculate success probability based on agent traits and situation
        success_prob = self._calculate_success_probability(agent, decision)
        success = random.random() < success_prob
        
        # Initialize result
        result = ActionExecutionResult(
            success=success,
            outcome="",
            impact={},
            side_effects=[],
            affected_agents=[],
            world_state_changes={},
        )
        
        # ── Semantic routing ──────────────────────────────────────────────────
        # Embed the LLM's action string and find the closest handler (~3ms GPU)
        handler_name, similarity = action_router.route(decision.action)
        logger.debug(f"Routed '{decision.action}' -> {handler_name} (sim={similarity:.3f})")

        handler_map = {
            "gather_information":   lambda: self._execute_gather_information(db, agent, decision, world_state),
            "expansion":            lambda: self._execute_expansion(db, agent, decision, world_state, success),
            "product_launch":       lambda: self._execute_product_launch(db, agent, decision, world_state, success),
            "acquisition":          lambda: self._execute_acquisition(db, agent, decision, world_state, success),
            "alliance":             lambda: self._execute_alliance(db, agent, decision, world_state, success),
            "attack":               lambda: self._execute_attack(db, agent, decision, world_state, success),
            "negotiation":          lambda: self._execute_negotiation(db, agent, decision, world_state, success),
            "investment":           lambda: self._execute_investment(db, agent, decision, world_state, success),
            "policy":               lambda: self._execute_policy(db, agent, decision, world_state, success),
            "sabotage":             lambda: self._execute_sabotage(db, agent, decision, world_state, success),
            "campaign":             lambda: self._execute_campaign(db, agent, decision, world_state, success),
            "relationship_building":lambda: self._execute_help(db, agent, decision, world_state, success),
            "observe":              lambda: self._execute_observe(db, agent, decision, world_state, success),
            "talent":               lambda: self._execute_talent(db, agent, decision, world_state, success),
            "financial":            lambda: self._execute_financial(db, agent, decision, world_state, success),
        }

        handler = handler_map.get(handler_name)
        if handler:
            result = await handler()
        else:
            result = await self._execute_generic(db, agent, decision, world_state, success)
        
        # Apply world state changes
        if result.world_state_changes and world_state:
            for key, value in result.world_state_changes.items():
                if world_state.state is None:
                    world_state.state = {}
                world_state.state[key] = value
            await db.commit()
        
        # Create action record
        action_record = AgentAction(
            id=uuid4(),
            agent_id=agent.id,
            project_id=agent.project_id,
            simulation_step=simulation_step,
            action_type=decision.action,
            description=decision.action,
            reasoning=decision.reasoning,
            confidence=decision.confidence,
            executed=True,
            success=result.success,
            outcome=result.outcome,
            impact=result.impact,
            created_at=datetime.utcnow(),
            executed_at=datetime.utcnow(),
        )
        db.add(action_record)
        
        # Create world event
        # First, get or create world state
        from backend.models.world_models import WorldState
        result_ws = await db.execute(
            select(WorldState).where(WorldState.project_id == agent.project_id)
        )
        world_state_obj = result_ws.scalar_one_or_none()
        
        if not world_state_obj:
            # Create world state if it doesn't exist
            world_state_obj = WorldState(
                id=uuid4(),
                project_id=agent.project_id,
                state={},
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
            )
            db.add(world_state_obj)
            await db.commit()
            await db.refresh(world_state_obj)
        
        event = WorldEvent(
            id=uuid4(),
            world_state_id=world_state_obj.id,
            event_type="agent_action",
            description=f"{agent.name} ({agent.role}): {result.outcome}",
            impact_score=0.5 if result.success else 0.2,
            occurred_at=datetime.utcnow(),
        )
        db.add(event)
        
        # Store as memory
        memory_manager = AgentMemoryManager(agent.id)
        await memory_manager.remember(
            db,
            memory_type="observation",
            content=result.outcome,
            importance=0.7 if result.success else 0.5,
            emotional_valence=0.5 if result.success else -0.3,
        )
        
        await db.commit()
        
        logger.info(f"Action executed: {result.outcome}")
        return result, action_record
    
    def _calculate_success_probability(self, agent: Agent, decision: AgentDecision) -> float:
        """Calculate probability of action success based on agent traits"""
        base_prob = 0.6
        
        # Confidence affects success
        base_prob += (decision.confidence - 0.5) * 0.2
        
        # Personality affects success
        personality = agent.personality
        
        # Rational agents have higher success in analytical tasks
        if personality.get("rationality", 0.5) > 0.7:
            base_prob += 0.1
        
        # Ambitious agents push harder
        if personality.get("ambition", 0.5) > 0.7:
            base_prob += 0.05
        
        # Risk-tolerant agents might fail more on risky actions
        if personality.get("risk_tolerance", 0.5) > 0.7:
            base_prob -= 0.05
        
        return max(0.1, min(0.95, base_prob))
    
    async def _execute_gather_information(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: WorldState,
    ) -> ActionExecutionResult:
        """
        Execute information gathering.

        - Always succeeds (no random failure — failing to gather info is unrealistic)
        - Produces specific named discoveries via WorldKnowledgeSystem
        - Updates the primary goal's knowledge_score
        - Stores each discovery as a 'discovery' memory
        """
        goal_manager = GoalManager(agent.id)
        memory_manager = AgentMemoryManager(agent.id)

        # Get primary goal
        active_goals = await goal_manager.get_active_goals(db, limit=1)
        primary_goal = active_goals[0] if active_goals else None
        goal_type = primary_goal.goal_type if primary_goal else "wealth"

        # Load already-discovered facts to avoid repeats
        from sqlalchemy import select as sa_select
        from backend.models.agent_models import AgentMemory
        result = await db.execute(
            sa_select(AgentMemory).where(
                AgentMemory.agent_id == agent.id,
                AgentMemory.memory_type == "discovery",
            )
        )
        existing = [m.content for m in result.scalars().all()]

        # Get new discoveries
        discoveries, knowledge_gain, narrative = world_knowledge.gather_information(
            agent=agent,
            goal_type=goal_type,
            existing_discoveries=existing,
        )

        # Store each discovery as a high-importance memory
        for fact in discoveries:
            await memory_manager.remember(
                db,
                memory_type="discovery",
                content=fact,
                importance=0.85,
                emotional_valence=0.4,
            )

        # Update goal knowledge_score
        if primary_goal:
            updated_goal = await goal_manager.update_knowledge_score(
                db, primary_goal.id, knowledge_gain
            )
            new_score = updated_goal.knowledge_score if updated_goal else 0.0
            threshold_note = (
                f" [Knowledge score: {new_score:.0%} — READY TO ACT]"
                if new_score >= 0.65
                else f" [Knowledge score: {new_score:.0%} / 65% threshold]"
            )
        else:
            threshold_note = ""

        return ActionExecutionResult(
            success=True,
            outcome=narrative + threshold_note,
            impact={"knowledge_gain": knowledge_gain, "facts_discovered": len(discoveries)},
            side_effects=[f"Discovered: {d[:60]}..." for d in discoveries],
        )

    async def _execute_expansion(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute business/territory expansion"""
        if success:
            growth = random.uniform(0.1, 0.3)
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully expanded operations, growing by {growth*100:.1f}%",
                impact={"growth": growth, "market_share": growth * 0.5},
                world_state_changes={f"agent_{agent.id}_size": growth},
                side_effects=["Increased visibility", "Attracted competitors"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s expansion attempt failed due to market resistance",
                impact={"growth": -0.05},
                side_effects=["Lost resources", "Damaged reputation"],
            )
    
    async def _execute_product_launch(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute product launch"""
        if success:
            innovation_score = random.uniform(0.6, 1.0)
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} launched innovative product with {innovation_score*100:.0f}% market reception",
                impact={"innovation": innovation_score, "revenue": innovation_score * 0.3},
                world_state_changes={f"product_count": 1},
                side_effects=["Market disruption", "Competitor response likely"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s product launch flopped, poor market fit",
                impact={"revenue": -0.1, "reputation": -0.2},
                side_effects=["Wasted R&D investment"],
            )
    
    async def _execute_acquisition(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute company/asset acquisition"""
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully acquired target, consolidating market position",
                impact={"market_share": 0.15, "resources": 0.2},
                world_state_changes={"consolidation": 1},
                side_effects=["Regulatory scrutiny", "Integration challenges"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s acquisition blocked by regulators or outbid by competitor",
                impact={"resources": -0.1},
                side_effects=["Public embarrassment"],
            )
    
    async def _execute_alliance(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute alliance formation"""
        # Find potential allies
        result = await db.execute(
            select(Agent).where(
                Agent.project_id == agent.project_id,
                Agent.id != agent.id
            ).limit(5)
        )
        potential_allies = list(result.scalars().all())
        
        if success and potential_allies:
            ally = random.choice(potential_allies)
            
            # Create/update relationship
            rel_manager = RelationshipManager(agent.id)
            await rel_manager.record_interaction(
                db,
                project_id=agent.project_id,
                other_agent_id=ally.id,
                interaction_type="cooperation",
                description=f"Formed strategic alliance",
                outcome="positive",
                trust_change=0.3,
                strength_change=0.4,
            )
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} formed alliance with {ally.name}",
                impact={"influence": 0.2, "security": 0.3},
                affected_agents=[ally.id],
                side_effects=["Mutual defense pact", "Shared resources"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s alliance proposal rejected",
                impact={"reputation": -0.1},
                side_effects=["Diplomatic embarrassment"],
            )
    
    async def _execute_attack(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute attack/aggressive action"""
        # Find potential targets
        result = await db.execute(
            select(Agent).where(
                Agent.project_id == agent.project_id,
                Agent.id != agent.id
            ).limit(5)
        )
        potential_targets = list(result.scalars().all())
        
        if potential_targets:
            target = random.choice(potential_targets)
            
            # Update relationship
            rel_manager = RelationshipManager(agent.id)
            await rel_manager.record_interaction(
                db,
                project_id=agent.project_id,
                other_agent_id=target.id,
                interaction_type="attack",
                description=f"Launched attack",
                outcome="negative",
                trust_change=-0.5,
                strength_change=-0.6,
            )
            
            if success:
                return ActionExecutionResult(
                    success=True,
                    outcome=f"{agent.name} successfully attacked {target.name}, gaining advantage",
                    impact={"power": 0.3, "resources": 0.2},
                    affected_agents=[target.id],
                    side_effects=["Created enemy", "Escalation risk"],
                )
            else:
                return ActionExecutionResult(
                    success=False,
                    outcome=f"{agent.name}'s attack on {target.name} repelled",
                    impact={"power": -0.2, "reputation": -0.3},
                    affected_agents=[target.id],
                    side_effects=["Weakened position", "Retaliation expected"],
                )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} found no suitable target for attack",
                impact={},
            )
    
    async def _execute_negotiation(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute negotiation"""
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully negotiated favorable terms",
                impact={"influence": 0.2, "resources": 0.15},
                side_effects=["Improved diplomatic standing"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s negotiation stalled, no agreement reached",
                impact={"influence": -0.05},
                side_effects=["Wasted time"],
            )
    
    async def _execute_investment(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute investment/R&D"""
        if success:
            # Update goal progress if relevant
            goal_manager = GoalManager(agent.id)
            goals = await goal_manager.get_active_goals(db)
            for goal in goals:
                if "innovation" in goal.goal_type or "knowledge" in goal.goal_type:
                    await goal_manager.update_progress(db, goal.id, goal.progress + 0.2)
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} invested successfully, breakthrough achieved",
                impact={"innovation": 0.4, "future_potential": 0.5},
                side_effects=["Competitive advantage gained"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s investment yielded no results",
                impact={"resources": -0.15},
                side_effects=["Wasted capital"],
            )
    
    async def _execute_policy(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute policy proposal"""
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully passed new policy",
                impact={"influence": 0.3, "control": 0.2},
                world_state_changes={"policy_count": 1},
                side_effects=["Public reaction mixed", "Implementation challenges"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s policy proposal blocked by opposition",
                impact={"influence": -0.1},
                side_effects=["Political capital lost"],
            )
    
    async def _execute_sabotage(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute sabotage/covert action"""
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully sabotaged target without detection",
                impact={"advantage": 0.3},
                side_effects=["Target weakened", "Risk of discovery"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s sabotage attempt discovered and failed",
                impact={"reputation": -0.4, "security": -0.3},
                side_effects=["Identity compromised", "Retaliation incoming"],
            )
    
    async def _execute_help(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute helping/support action"""
        # Find someone to help
        result = await db.execute(
            select(Agent).where(
                Agent.project_id == agent.project_id,
                Agent.id != agent.id
            ).limit(5)
        )
        potential_targets = list(result.scalars().all())
        
        if potential_targets:
            target = random.choice(potential_targets)
            
            # Update relationship
            rel_manager = RelationshipManager(agent.id)
            await rel_manager.record_interaction(
                db,
                project_id=agent.project_id,
                other_agent_id=target.id,
                interaction_type="support",
                description=f"Provided assistance",
                outcome="positive",
                trust_change=0.2,
                strength_change=0.3,
            )
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} helped {target.name}, building goodwill",
                impact={"reputation": 0.2, "relationships": 0.3},
                affected_agents=[target.id],
                side_effects=["Gained ally", "Positive reputation"],
            )
        else:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} helped the community",
                impact={"reputation": 0.1},
            )
    
    async def _execute_observe(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute observation/waiting"""
        return ActionExecutionResult(
            success=True,
            outcome=f"{agent.name} observed the situation and gathered information",
            impact={"knowledge": 0.1},
            side_effects=["Better informed for future decisions"],
        )
    
    async def _execute_campaign(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute public campaign, media exposure, activist action."""
        action = decision.action
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully executed public campaign: {action}. "
                        f"The story gained traction and public pressure is mounting.",
                impact={"influence": 0.3, "public_pressure": 0.4, "reputation": 0.2},
                side_effects=["Media coverage generated", "Target on defensive", "Public awareness raised"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s campaign '{action}' was suppressed or ignored by media.",
                impact={"influence": -0.05},
                side_effects=["Message didn't land", "Try a different channel"],
            )

    async def _execute_talent(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute talent acquisition — hire, recruit, or poach key people."""
        action = decision.action
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully recruited key talent: {action}. "
                        f"Competitor weakened, team strengthened.",
                impact={"talent": 0.3, "competitor_weakness": 0.2, "innovation": 0.15},
                side_effects=["Competitor lost key person", "Knowledge transfer gained"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} failed to recruit — candidate declined or was counter-offered.",
                impact={"resources": -0.05},
                side_effects=["Competitor retained talent", "Try higher offer"],
            )

    async def _execute_financial(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """Execute financial operations — funding, cost cuts, cash management."""
        action = decision.action
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully executed financial operation: {action}.",
                impact={"resources": 0.25, "financial_stability": 0.2},
                side_effects=["Improved financial position", "More runway secured"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s financial operation '{action}' fell through.",
                impact={"resources": -0.1},
                side_effects=["Financial pressure remains"],
            )

    async def _execute_generic(
        self, db: AsyncSession, agent: Agent, decision: AgentDecision,
        world_state: WorldState, success: bool
    ) -> ActionExecutionResult:
        """
        Fallback for actions the router couldn't confidently match.
        Uses a higher success rate since these are usually valid execution actions.
        """
        action = decision.action
        # Re-roll with higher base rate — if the agent chose it, it's probably valid
        success = random.random() < 0.80
        if success:
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully executed: {action}. The intelligence gathered paid off.",
                impact={"goal_progress": 0.2, "influence": 0.1},
                side_effects=["Progress made toward goal"],
            )
        else:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s attempt to '{action}' was partially blocked, but progress was made.",
                impact={"goal_progress": 0.05},
                side_effects=["Partial setback — try again or adapt"],
            )
