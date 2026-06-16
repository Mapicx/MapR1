"""
MapR1 — Action Executor V2 (Phase 2)

Context-aware action executors that:
1. Use relationships and discoveries for target selection (not random)
2. Mutate structured world state consistently
3. Create real consequences for failures
4. Log events with visibility for feedback loop

This is the Phase 2 implementation. Once tested, it will replace action_executor.py.
"""

import random
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models.agent_models import Agent
from backend.models.action_models import AgentDecision, ActionExecutionResult
from backend.models.world_models import (
    WorldState,
    StructuredWorldState,
    AllianceRecord,
    RivalryRecord,
    WorldEventRecord,
)
from backend.agents.relationship_system import RelationshipManager
from backend.agents.agent_memory import AgentMemoryManager
from backend.agents.goal_system import GoalManager
from backend.agents.world_knowledge import world_knowledge
from backend.simulation.contextual_consequence_engine import ContextualConsequenceEngine


class ActionExecutorV2:
    """
    Phase 2 action executor with context-aware targeting and real consequences.
    """

    def __init__(self):
        self.contextual_engine = ContextualConsequenceEngine()
        from backend.systems.public_opinion_system import PublicOpinionSystem
        self.public_opinion_system = PublicOpinionSystem()

    # ── Core Executors (Phase 2 - 50%) ──────────────────────────────────────

    async def _apply_contextual_success(
        self,
        db: AsyncSession,
        action_family: str,
        agent: Agent,
        target: 'Agent | None',
        structured: StructuredWorldState,
        simulation_step: int,
        world_state: 'WorldState | None',
    ) -> tuple:
        """
        Apply contextual secondary effects for a successful action.
        
        Returns:
            (outcome, description) — the selected contextual outcome and its formatted description.
            The outcome's secondary effects (psychology, memory, events, delayed) have been applied.
        """
        ctx = await self.contextual_engine.build_context(db, agent, target, structured)
        outcome, description = self.contextual_engine.resolve_success(
            action_family, agent, target, ctx
        )
        await self.contextual_engine.apply_secondary_effects(
            db, agent, target, outcome, structured, simulation_step, world_state
        )
        return outcome, description

    async def _apply_contextual_failure(
        self,
        db: AsyncSession,
        action_family: str,
        agent: Agent,
        target: 'Agent | None',
        structured: StructuredWorldState,
        simulation_step: int,
        world_state: 'WorldState | None',
    ) -> tuple:
        """
        Apply contextual consequences for a failed action.
        
        Returns:
            (outcome, description) — the selected contextual outcome and its formatted description.
            The outcome's secondary effects (psychology, memory, events, delayed) have been applied.
        """
        ctx = await self.contextual_engine.build_context(db, agent, target, structured)
        outcome, description = self.contextual_engine.resolve_failure(
            action_family, agent, target, ctx
        )
        await self.contextual_engine.apply_secondary_effects(
            db, agent, target, outcome, structured, simulation_step, world_state
        )
        return outcome, description


    async def execute_alliance(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="ally")
        
        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not find a suitable alliance partner",
                impact={"influence": -0.05},
                side_effects=["No willing partners found"],
            )
            
        structured = self._get_structured_state(world_state)
        
        proposal = {
            "id": str(uuid4()),
            "type": "alliance",
            "from_agent_id": str(agent.id),
            "from_agent_name": agent.name,
            "to_agent_id": str(target.id),
            "to_agent_name": target.name,
            "step_created": simulation_step,
            "context": decision.reasoning
        }
        structured.pending_proposals.append(proposal)
        self._save_structured_state(world_state, structured)
        
        return ActionExecutionResult(
            success=True,
            outcome=f"{agent.name} formally proposed an alliance to {target.name}.",
            impact={},
            world_state_changes=structured.to_dict(),
        )


    async def execute_sabotage(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Sabotage — actually hurts the target, but has real exposure risk.
        
        Rules:
        - Target selected from decision context or agent's rivals
        - On success: target loses resources & reputation, event logged with LOW visibility
        - On failure: agent is EXPOSED — reputation tanks, target's trust goes to 0,
          ALL agents learn about it (high visibility event), retaliation flag set
        """
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        
        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not identify a target for sabotage",
                impact={},
                side_effects=["No suitable target found"],
            )
        
        structured = self._get_structured_state(world_state)
        
        if success:
            # Target actually takes damage
            structured.agent_resources[str(target.id)] = max(0.02, 
                structured.agent_resources.get(str(target.id), 0.5) - 0.2)
            structured.agent_reputation[str(target.id)] = max(0,
                structured.agent_reputation.get(str(target.id), 0.5) - 0.15)
            
            # Low visibility — sabotage was covert
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor="unknown",  # covert!
                action="sabotage",
                target=target.name,
                outcome=f"{target.name} suffered an unexplained setback",
                visibility=0.2,  # Only target notices
            ))
            
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "sabotage", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Sabotage successful: {agent.name} → {target.name} (covert) [{ctx_outcome.key}]")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} covertly sabotaged {target.name}, causing resource loss. {ctx_desc}",
                impact={"advantage": 0.3, "target_resources": -0.2},
                affected_agents=[target.id],
                side_effects=[
                    f"{target.name} weakened but doesn't know who did it",
                    f"Secondary: {ctx_outcome.key}",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            # FAILURE: Use contextual consequence engine
            ctx = await self.contextual_engine.build_context(db, agent, target, structured)
            outcome, description = self.contextual_engine.resolve_failure(
                "sabotage", agent, target, ctx
            )
            await self.contextual_engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step, world_state
            )
            
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Sabotage FAILED: {agent.name} → {target.name} [{outcome.key}]")
            
            return ActionExecutionResult(
                success=False,
                outcome=description,
                impact={
                    "reputation": outcome.actor_reputation_delta,
                    "exposure": outcome.actor_exposure_delta,
                    "resources": outcome.actor_resources_delta,
                },
                affected_agents=[target.id],
                side_effects=[
                    f"Consequence: {outcome.key}",
                    f"{target.name}'s trust severely damaged" if outcome.target_trust_delta < -0.5 else "Tension increased",
                    "Retaliation likely" if outcome.creates_rivalry else "Situation contained",
                ],
                world_state_changes=structured.to_dict(),
            )

    async def execute_campaign(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Public campaign — actually shifts public opinion and media attention.
        
        Rules:
        - On success: public_opinion shifts on relevant topic, media_attention increases,
          target's regulatory_pressure increases
        - On failure: small resource cost, campaign is forgotten
        - Cumulative: multiple successful campaigns compound pressure
        """
        structured = self._get_structured_state(world_state)
        
        # Determine campaign topic from decision context
        topic = self._extract_campaign_topic(decision)
        
        if success:
            # Shift public opinion nonlinearly
            event_msg = self.public_opinion_system.push_opinion(structured, topic, 0.25)
            if event_msg:
                # Store the threshold crossing event for the agent to see
                structured.recent_events.append(WorldEventRecord(
                    step=simulation_step,
                    actor="system",
                    action="opinion_shift",
                    outcome=event_msg,
                    visibility=1.0
                ))
            
            # Increase media attention
            current_media = structured.media_attention.get(topic, 0.0)
            structured.media_attention[topic] = min(1.0, current_media + 0.3)
            
            # If target company identified, increase regulatory pressure
            target_entity = self._extract_target_entity(decision)
            if target_entity:
                current_pressure = structured.regulatory_pressure.get(target_entity, 0.0)
                structured.regulatory_pressure[target_entity] = min(1.0, current_pressure + 0.2)
            
            # Boost agent's reputation (activist visibility)
            structured.agent_reputation[str(agent.id)] = min(1.0,
                structured.agent_reputation.get(str(agent.id), 0.5) + 0.15)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="public_campaign",
                target=target_entity,
                outcome=f"{agent.name}'s campaign on '{topic}' gained major traction. "
                        f"Public opinion: {structured.public_opinion[topic]:.0%} favorable",
                visibility=0.9,
            ))
            
            self._save_structured_state(world_state, structured)
            
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "campaign", agent, None, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(
                f"✓ Campaign success: {agent.name} on '{topic}' "
                f"(opinion: {structured.public_opinion[topic]:.0%}) [{ctx_outcome.key}]"
            )
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name}'s campaign shifted public opinion on '{topic}' to "
                        f"{structured.public_opinion[topic]:.0%} favorable. "
                        f"Media attention: {structured.media_attention[topic]:.0%}. {ctx_desc}",
                impact={"public_opinion": 0.25, "media_attention": 0.3, "reputation": 0.15},
                side_effects=[
                    f"Public pressure on {target_entity} increasing" if target_entity else "Awareness raised",
                    "Media covering the story",
                    "Potential regulatory response",
                    f"Secondary: {ctx_outcome.key}",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "campaign", agent, None, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s campaign on '{topic}' failed. {ctx_desc}",
                impact={},
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict(),
            )

    async def execute_attack(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Attack — direct confrontation with real consequences.
        
        Rules:
        - Target selected from decision context or known rivals
        - On success: target loses resources/power, RivalryRecord created, high visibility
        - On failure: attacker loses power, retaliation flag, exposure
        """
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        
        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not identify a target for attack",
                impact={},
                side_effects=["No suitable target found"],
            )
        
        structured = self._get_structured_state(world_state)
        
        if success:
            # Target takes damage
            structured.agent_resources[str(target.id)] = max(0.02,
                structured.agent_resources.get(str(target.id), 0.5) - 0.25)
            structured.agent_power[str(target.id)] = max(0,
                structured.agent_power.get(str(target.id), 0.5) - 0.20)
            
            # Attacker gains some power
            structured.agent_power[str(agent.id)] = min(1.0,
                structured.agent_power.get(str(agent.id), 0.5) + 0.10)
            
            # Create or intensify rivalry
            existing_rivalry = next(
                (r for r in structured.rivalries 
                 if {r.agent_a, r.agent_b} == {str(agent.id), str(target.id)}),
                None
            )
            
            if existing_rivalry:
                existing_rivalry.intensity = min(1.0, existing_rivalry.intensity + 0.2)
            else:
                structured.rivalries.append(RivalryRecord(
                    agent_a=str(agent.id),
                    agent_b=str(target.id),
                    started_at_step=simulation_step,
                    intensity=0.7,
                    cause="attack",
                ))
            
            # High visibility event
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="attack",
                target=target.name,
                outcome=f"{agent.name} attacked {target.name}, causing significant damage",
                visibility=0.9,
            ))
            
            self._save_structured_state(world_state, structured)
            
            # Update relationship
            rel_manager = RelationshipManager(agent.id)
            await rel_manager.record_interaction(
                db,
                project_id=world_state.project_id if world_state else agent.id,
                other_agent_id=target.id,
                interaction_type="attack",
                description=f"Attacked {target.name}",
                outcome="positive",
                trust_change=-0.8,
                strength_change=-0.6,
            )
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "attack", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Attack successful: {agent.name} → {target.name} [{ctx_outcome.key}]")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully attacked {target.name}. {ctx_desc}",
                impact={"power": 0.10, "target_resources": -0.25},
                affected_agents=[target.id],
                side_effects=[
                    f"{target.name} significantly weakened",
                    "Rivalry intensified",
                    f"Secondary: {ctx_outcome.key}",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "attack", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Attack failed: {agent.name} → {target.name}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s attack on {target.name} failed. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict(),
            )

    # ── Helper Methods ──────────────────────────────────────────────────────

    async def _resolve_target_agent(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        preference: str = "any",  # kept for signature compatibility but ignored
    ) -> Optional[Agent]:
        """
        Intelligently resolve which agent the action targets.
        
        Priority order:
        1. Agent mentioned by name in decision.affected_agents
        2. Agent mentioned by name in decision.reasoning
        """
        # Step 1: Get all other agents in project
        result = await db.execute(
            select(Agent).where(
                Agent.project_id == agent.project_id,
                Agent.id != agent.id
            )
        )
        agents = list(result.scalars().all())
        
        # Filter out collapsed agents unless action is exploitative
        allowed_against_collapsed = ["acquire_company", "exploit_vulnerability", "poach_talent"]
        if decision.action.lower() not in allowed_against_collapsed:
            agents = [a for a in agents if a.status != "collapsed"]
        
        if not agents:
            return None
            
        # Step 2: Check decision.affected_agents (highest priority)
        if decision.affected_agents:
            for name in decision.affected_agents:
                match = next((a for a in agents if a.name.lower() == name.lower()), None)
                if match:
                    logger.debug(f"Target resolved from affected_agents: {match.name}")
                    return match
        
        # Step 3: Check if agent name mentioned in reasoning
        for a in agents:
            if a.name.lower() in decision.reasoning.lower():
                logger.debug(f"Target resolved from reasoning: {a.name}")
                return a
        
        logger.warning(f"Could not resolve valid target from decision: affected_agents={decision.affected_agents}")
        return None

    def _get_structured_state(self, world_state: Optional[WorldState]) -> StructuredWorldState:
        """Get or create structured world state from WorldState object"""
        if not world_state or not world_state.state:
            return StructuredWorldState()
        
        # Check if already structured
        if isinstance(world_state.state, dict) and "agent_resources" in world_state.state:
            return StructuredWorldState.from_dict(world_state.state)
        
        # Migrate from legacy
        return StructuredWorldState.from_legacy_state(world_state.state)

    def _save_structured_state(self, world_state: Optional[WorldState], structured: StructuredWorldState):
        """Save structured state back to WorldState object"""
        if world_state:
            world_state.state = structured.to_dict()

    def _extract_campaign_topic(self, decision: AgentDecision) -> str:
        """Extract campaign topic from decision context"""
        # Look for keywords in reasoning
        reasoning_lower = decision.reasoning.lower()
        
        # Common topics
        if "environment" in reasoning_lower or "pollution" in reasoning_lower:
            return "environmental_accountability"
        if "labor" in reasoning_lower or "worker" in reasoning_lower:
            return "labor_rights"
        if "privacy" in reasoning_lower or "data" in reasoning_lower:
            return "data_privacy"
        if "tax" in reasoning_lower:
            return "tax_fairness"
        
        # Default
        return "corporate_accountability"

    def _extract_target_entity(self, decision: AgentDecision) -> Optional[str]:
        """Extract target entity/company name from decision"""
        # Look for company names in reasoning
        reasoning = decision.reasoning
        
        # Common company name patterns
        company_keywords = ["corp", "tech", "inc", "ltd", "company"]
        words = reasoning.split()
        
        for i, word in enumerate(words):
            if any(keyword in word.lower() for keyword in company_keywords):
                # Return the word (company name)
                return word.strip(".,!?")
        
        # Check affected_agents
        if decision.affected_agents:
            return decision.affected_agents[0]
        
        return None

    # ── Remaining Executors (Phase 2 - 50%) ─────────────────────────────────

    async def execute_expansion(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Business expansion — agent grows their operations.
        
        Rules:
        - Self-targeting action
        - On success: resources and power increase, market share grows
        - On failure: resources lost, competitors alerted
        """
        structured = self._get_structured_state(world_state)
        
        if success:
            # Agent gains resources and power
            structured.agent_resources[str(agent.id)] = min(1.0,
                structured.agent_resources.get(str(agent.id), 0.5) + 0.15)
            structured.agent_power[str(agent.id)] = min(1.0,
                structured.agent_power.get(str(agent.id), 0.5) + 0.10)
            
            # Update market conditions
            sector = agent.agent_type  # Use agent type as sector
            structured.market_conditions[sector] = min(1.0,
                structured.market_conditions.get(sector, 0.5) + 0.05)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="expansion",
                outcome=f"{agent.name} successfully expanded operations",
                visibility=0.6,
            ))
            
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Expansion successful: {agent.name}")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} expanded operations successfully",
                impact={"resources": 0.15, "power": 0.10},
                side_effects=["Market presence increased", "Competitors aware"],
                world_state_changes=structured.to_dict(),
            )
        else:
            # Failure: resources wasted
            structured.agent_resources[str(agent.id)] = max(0.02,
                structured.agent_resources.get(str(agent.id), 0.5) - 0.10)
            
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Expansion failed: {agent.name}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s expansion attempt failed",
                impact={"resources": -0.10},
                side_effects=["Resources wasted", "Opportunity missed"],
                world_state_changes=structured.to_dict(),
            )

    async def execute_acquisition(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Acquisition — absorb another agent/company.
        
        Rules:
        - Target selected from decision or weakest competitor
        - On success: target absorbed, agent gains their resources, target weakened
        - On failure: resources spent, regulatory scrutiny
        """
        target = await self._resolve_target_agent(db, agent, decision, preference="any")
        
        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not identify an acquisition target",
                impact={},
                side_effects=["No suitable target found"],
            )
        
        structured = self._get_structured_state(world_state)
        
        if success:
            # Transfer resources from target to agent
            target_resources = structured.agent_resources.get(str(target.id), 0.5)
            structured.agent_resources[str(agent.id)] = min(1.0,
                structured.agent_resources.get(str(agent.id), 0.5) + (target_resources * 0.5))
            
            # Weaken target significantly
            structured.agent_resources[str(target.id)] = max(0.02, target_resources * 0.3)
            structured.agent_power[str(target.id)] = max(0,
                structured.agent_power.get(str(target.id), 0.5) * 0.4)
            
            # Boost agent power
            structured.agent_power[str(agent.id)] = min(1.0,
                structured.agent_power.get(str(agent.id), 0.5) + 0.20)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="acquisition",
                target=target.name,
                outcome=f"{agent.name} acquired {target.name}",
                visibility=0.9,
            ))
            
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "acquisition", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Acquisition successful: {agent.name} → {target.name} [{ctx_outcome.key}]")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully acquired {target.name}. {ctx_desc}",
                impact={"power": 0.20, "resources": 0.15},
                affected_agents=[target.id],
                side_effects=[
                    f"{target.name} absorbed and weakened",
                    "Market consolidation",
                    f"Secondary: {ctx_outcome.key}",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "acquisition", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Acquisition failed: {agent.name} → {target.name}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s acquisition of {target.name} failed. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict(),
            )

    async def execute_negotiation(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Negotiation — diplomatic engagement for mutual benefit.
        
        Rules:
        - Target from decision or nearest relationship
        - On success: both sides gain, relationship strengthened
        - On failure: time wasted, slight reputation loss
        """
        target = await self._resolve_target_agent(db, agent, decision, preference="any")
        
        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not find a negotiation partner",
                impact={},
                side_effects=["No willing partners found"],
            )
        
        structured = self._get_structured_state(world_state)
        
        if success:
            # Both agents gain resources
            structured.agent_resources[str(agent.id)] = min(1.0,
                structured.agent_resources.get(str(agent.id), 0.5) + 0.10)
            structured.agent_resources[str(target.id)] = min(1.0,
                structured.agent_resources.get(str(target.id), 0.5) + 0.08)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="negotiation",
                target=target.name,
                outcome=f"{agent.name} and {target.name} reached a beneficial agreement",
                visibility=0.5,
            ))
            
            self._save_structured_state(world_state, structured)
            
            # Strengthen relationship
            rel_manager = RelationshipManager(agent.id)
            await rel_manager.record_interaction(
                db,
                project_id=world_state.project_id if world_state else agent.id,
                other_agent_id=target.id,
                interaction_type="cooperation",
                description=f"Negotiated agreement with {target.name}",
                outcome="positive",
                trust_change=0.15,
                strength_change=0.20,
            )
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "negotiation", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Negotiation successful: {agent.name} ↔ {target.name} [{ctx_outcome.key}]")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully negotiated with {target.name}. {ctx_desc}",
                impact={"resources": 0.10, "trust": 0.15},
                affected_agents=[target.id],
                side_effects=[
                    "Mutual resource gain",
                    "Relationship strengthened",
                    "Future cooperation more likely",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "negotiation", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Negotiation failed: {agent.name} ↔ {target.name}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s negotiation with {target.name} broke down. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict(),
            )

    async def execute_investment(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Investment — invest in R&D, innovation, future capabilities.
        
        Rules:
        - Self-targeting action
        - On success: innovation score up, future power boost (delayed effect)
        - On failure: resources lost
        """
        structured = self._get_structured_state(world_state)
        
        if success:
            # Immediate small resource cost
            structured.agent_resources[str(agent.id)] = max(0.02,
                structured.agent_resources.get(str(agent.id), 0.5) - 0.05)
            
            # Future power boost (represented by adding to power)
            structured.agent_power[str(agent.id)] = min(1.0,
                structured.agent_power.get(str(agent.id), 0.5) + 0.15)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="investment",
                outcome=f"{agent.name} invested in innovation and R&D",
                visibility=0.4,
            ))
            
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Investment successful: {agent.name}")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} invested successfully in R&D",
                impact={"power": 0.15, "resources": -0.05},
                side_effects=[
                    "Innovation capabilities increased",
                    "Future competitive advantage",
                    "Long-term growth potential",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            # Failure: resources lost
            structured.agent_resources[str(agent.id)] = max(0.02,
                structured.agent_resources.get(str(agent.id), 0.5) - 0.10)
            
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Investment failed: {agent.name}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s investment failed to yield results",
                impact={"resources": -0.10},
                side_effects=["Resources wasted", "No innovation gain"],
                world_state_changes=structured.to_dict(),
            )

    async def execute_policy(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Policy action — propose/implement policy changes.
        
        Rules:
        - Global effect on regulatory landscape
        - On success: regulatory landscape changes, agent influence up
        - On failure: political capital lost, opposition empowered
        """
        structured = self._get_structured_state(world_state)
        
        # Extract policy topic from decision
        policy_topic = self._extract_campaign_topic(decision)  # Reuse topic extraction
        
        if success:
            # Change regulatory landscape
            structured.regulatory_pressure[policy_topic] = min(1.0,
                structured.regulatory_pressure.get(policy_topic, 0.0) + 0.3)
            
            # Boost agent power/influence
            structured.agent_power[str(agent.id)] = min(1.0,
                structured.agent_power.get(str(agent.id), 0.5) + 0.20)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="policy",
                outcome=f"{agent.name} successfully implemented policy on {policy_topic}",
                visibility=0.9,
            ))
            
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "policy", agent, None, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Policy successful: {agent.name} on {policy_topic} [{ctx_outcome.key}]")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully implemented policy on {policy_topic}. {ctx_desc}",
                impact={"power": 0.20, "influence": 0.25},
                side_effects=[
                    "Regulatory landscape changed",
                    "Political influence increased",
                    "Opposition may mobilize",
                    f"Secondary: {ctx_outcome.key}",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            # Failure: Use contextual consequence engine
            ctx = await self.contextual_engine.build_context(db, agent, None, structured)
            outcome, description = self.contextual_engine.resolve_failure(
                "policy", agent, None, ctx
            )
            await self.contextual_engine.apply_secondary_effects(
                db, agent, None, outcome, structured, simulation_step, world_state
            )
            
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Policy failed: {agent.name} [{outcome.key}]")
            
            return ActionExecutionResult(
                success=False,
                outcome=description,
                impact={
                    "power": outcome.actor_power_delta,
                    "reputation": outcome.actor_reputation_delta,
                },
                side_effects=[
                    f"Consequence: {outcome.key}",
                    "Political capital lost",
                    "Opposition empowered" if outcome.actor_power_delta < -0.1 else "Credibility tested",
                ],
                world_state_changes=structured.to_dict(),
            )

    async def execute_talent(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Talent acquisition — poach key people from competitors.
        
        Rules:
        - Target from decision
        - On success: agent gains capability, target loses it, target becomes hostile
        - On failure: target retains talent and becomes hostile
        """
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        
        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not identify a talent poaching target",
                impact={},
                side_effects=["No suitable target found"],
            )
        
        structured = self._get_structured_state(world_state)
        
        if success:
            # Agent gains power, target loses it
            structured.agent_power[str(agent.id)] = min(1.0,
                structured.agent_power.get(str(agent.id), 0.5) + 0.12)
            structured.agent_power[str(target.id)] = max(0,
                structured.agent_power.get(str(target.id), 0.5) - 0.10)
            
            # Target becomes hostile
            existing_rivalry = next(
                (r for r in structured.rivalries 
                 if {r.agent_a, r.agent_b} == {str(agent.id), str(target.id)}),
                None
            )
            
            if existing_rivalry:
                existing_rivalry.intensity = min(1.0, existing_rivalry.intensity + 0.15)
            else:
                structured.rivalries.append(RivalryRecord(
                    agent_a=str(target.id),
                    agent_b=str(agent.id),
                    started_at_step=simulation_step,
                    intensity=0.5,
                    cause="talent_poaching",
                ))
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="talent_poaching",
                target=target.name,
                outcome=f"{agent.name} poached key talent from {target.name}",
                visibility=0.6,
            ))
            
            self._save_structured_state(world_state, structured)
            
            # Damage relationship
            rel_manager = RelationshipManager(target.id)
            await rel_manager.record_interaction(
                db,
                project_id=world_state.project_id if world_state else agent.id,
                other_agent_id=agent.id,
                interaction_type="betrayal",
                description=f"{agent.name} poached our talent",
                outcome="negative",
                trust_change=-0.4,
                strength_change=-0.3,
            )
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "talent", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Talent poaching successful: {agent.name} → {target.name} [{ctx_outcome.key}]")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully poached talent from {target.name}. {ctx_desc}",
                impact={"power": 0.12},
                affected_agents=[target.id],
                side_effects=[
                    f"{target.name} weakened",
                    "Rivalry created/intensified",
                    "Competitive advantage gained",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            # Failure: target retains and becomes hostile
            structured.agent_reputation[str(agent.id)] = max(0,
                structured.agent_reputation.get(str(agent.id), 0.5) - 0.10)
            
            # Create rivalry
            structured.rivalries.append(RivalryRecord(
                agent_a=str(target.id),
                agent_b=str(agent.id),
                started_at_step=simulation_step,
                intensity=0.4,
                cause="failed_poaching_attempt",
            ))
            
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Talent poaching failed: {agent.name} → {target.name}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s attempt to poach talent from {target.name} failed",
                impact={"reputation": -0.10},
                affected_agents=[target.id],
                side_effects=[
                    "Poaching attempt exposed",
                    "Target now hostile",
                    "Reputation damaged",
                ],
                world_state_changes=structured.to_dict(),
            )


    # ── Gather Intel ────────────────────────────────────────────────────────
    
    async def execute_gather_intel(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Execute information gathering.

        - Always succeeds (gathering info shouldn't randomly fail)
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
        from backend.models.agent_models import AgentMemory
        result = await db.execute(
            select(AgentMemory).where(
                AgentMemory.agent_id == agent.id,
                AgentMemory.memory_type == "discovery",
            )
        )
        existing = [m.content for m in result.scalars().all()]

        # Get new discoveries from world knowledge system
        discoveries, knowledge_gain, narrative = world_knowledge.gather_information(
            agent=agent,
            goal_type=goal_type,
            existing_discoveries=existing,
        )

        # Store each discovery as a high-importance memory
        from backend.systems.fog_system import FogOfWarSystem
        fog_system = FogOfWarSystem()
        project_id = world_state.project_id if world_state else agent.id

        for fact in discoveries:
            await memory_manager.remember(
                db,
                memory_type="discovery",
                content=fact,
                importance=0.85,
                emotional_valence=0.4,
            )
            # Write to belief state for intel sharing
            await fog_system._reveal_fact(
                db,
                project_id=project_id,
                agent=agent,
                topic=fact,
                actor_name=agent.name,
                confidence=0.5,
                current_step=simulation_step
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

        logger.info(
            f"✓ Gather information: {agent.name} discovered {len(discoveries)} facts, "
            f"knowledge_gain={knowledge_gain:.2f}"
        )

        return ActionExecutionResult(
            success=True,
            outcome=narrative + threshold_note,
            impact={"knowledge_gain": knowledge_gain, "facts_discovered": len(discoveries)},
            side_effects=[f"Discovered: {d[:60]}..." for d in discoveries],
            public_impact=False,
        )

    # ── Action Router ───────────────────────────────────────────────────────

    async def execute_contract_bid(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        structured = self._get_structured_state(world_state)
        
        if success:
            structured.agent_resources[str(agent.id)] = min(1.0, structured.agent_resources.get(str(agent.id), 0.5) + 0.3)
            structured.agent_power[str(agent.id)] = min(1.0, structured.agent_power.get(str(agent.id), 0.5) + 0.15)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="bid_on_contract", target="Government",
                outcome=f"{agent.name} secured a major government contract", visibility=1.0
            ))
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=True, outcome=f"{agent.name} won the contract bid.", impact={"resources": 0.3, "power": 0.15},
                world_state_changes=structured.to_dict()
            )
        else:
            structured.agent_resources[str(agent.id)] = max(0.02, structured.agent_resources.get(str(agent.id), 0.5) - 0.1)
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False, outcome=f"{agent.name} lost the contract bid.", impact={"resources": -0.1},
                world_state_changes=structured.to_dict()
            )

    async def execute_lobbying(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        if not target:
            return ActionExecutionResult(success=False, outcome="No lobbying target found.", impact={})
            
        structured = self._get_structured_state(world_state)
        if success:
            structured.agent_power[str(target.id)] = max(0.0, structured.agent_power.get(str(target.id), 0.5) - 0.15)
            structured.agent_power[str(agent.id)] = min(1.0, structured.agent_power.get(str(agent.id), 0.5) + 0.15)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="lobby", target=target.name,
                outcome=f"Rumors of {agent.name} swaying {target.name}'s backers", visibility=0.3
            ))
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "lobbying", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            return ActionExecutionResult(
                success=True, 
                outcome=f"{agent.name} successfully lobbied against {target.name}. {ctx_desc}",
                impact={"power": 0.15}, 
                affected_agents=[target.id], 
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "lobbying", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s lobbying failed. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )

    async def execute_legal_action(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        if not target:
            return ActionExecutionResult(success=False, outcome="No target found for legal action.", impact={})
            
        structured = self._get_structured_state(world_state)
        if success:
            structured.agent_resources[str(target.id)] = max(0.02, structured.agent_resources.get(str(target.id), 0.5) - 0.2)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="legal_action", target=target.name,
                outcome=f"{agent.name} won a major legal victory against {target.name}", visibility=1.0
            ))
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "legal_action", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            return ActionExecutionResult(
                success=True, 
                outcome=f"{agent.name} crippled {target.name} legally. {ctx_desc}",
                impact={"target_resources": -0.2}, 
                affected_agents=[target.id], 
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "legal_action", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} lost the lawsuit. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )

    async def execute_media_campaign(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        if not target:
            return ActionExecutionResult(success=False, outcome="No target found for media campaign.", impact={})
            
        structured = self._get_structured_state(world_state)
        if success:
            structured.agent_reputation[str(target.id)] = max(0.0, structured.agent_reputation.get(str(target.id), 0.5) - 0.25)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="media_campaign", target=target.name,
                outcome=f"Devastating media expose on {target.name}", visibility=1.0
            ))
            
            # Spread Misinformation/Belief
            from backend.systems.trust_system import TrustMisinformationSystem
            trust_system = TrustMisinformationSystem()
            topic = f"{target.name} is corrupt or dangerous"
            await trust_system.spread_belief(db, agent.project_id, agent, topic, target_confidence=0.9, visibility=1.0)
            
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "media_campaign", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            return ActionExecutionResult(
                success=True, 
                outcome=f"{agent.name} destroyed {target.name}'s reputation publicly and shifted public belief. {ctx_desc}",
                impact={"target_reputation": -0.25}, 
                affected_agents=[target.id], 
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "media_campaign", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s media campaign failed. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )

    async def execute_hostile_takeover(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        if not target:
            return ActionExecutionResult(success=False, outcome="No target found for takeover.", impact={})
            
        structured = self._get_structured_state(world_state)
        if success:
            target_res = structured.agent_resources.get(str(target.id), 0.5)
            structured.agent_resources[str(target.id)] = max(0.02, target_res - 0.4)
            structured.agent_resources[str(agent.id)] = min(1.0, structured.agent_resources.get(str(agent.id), 0.5) + target_res * 0.8)
            structured.agent_power[str(agent.id)] = min(1.0, structured.agent_power.get(str(agent.id), 0.5) + 0.2)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="hostile_takeover", target=target.name,
                outcome=f"{agent.name} successfully executed a hostile takeover of {target.name}", visibility=1.0
            ))
            self._save_structured_state(world_state, structured)
            
            # Contextual success consequences
            ctx_outcome, ctx_desc = await self._apply_contextual_success(
                db, "hostile_takeover", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            
            return ActionExecutionResult(
                success=True, 
                outcome=f"{agent.name} seized {target.name}'s assets. {ctx_desc}",
                impact={"resources": 0.4, "power": 0.2}, 
                affected_agents=[target.id], 
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )
        else:
            ctx_outcome, ctx_desc = await self._apply_contextual_failure(
                db, "hostile_takeover", agent, target, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s takeover attempt failed. {ctx_desc}",
                impact={},
                affected_agents=[target.id],
                side_effects=[f"Secondary: {ctx_outcome.key}"],
                world_state_changes=structured.to_dict()
            )

    async def execute_poach_talent(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """Redirect to execute_talent — consolidated duplicate."""
        return await self.execute_talent(db, agent, decision, world_state, simulation_step, success)


    async def execute_exploit_vulnerability(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        if not target:
            return ActionExecutionResult(success=False, outcome="No vulnerability target found.", impact={})
            
        structured = self._get_structured_state(world_state)
        if success:
            structured.agent_resources[str(target.id)] = max(0.02, structured.agent_resources.get(str(target.id), 0.5) - 0.25)
            structured.agent_power[str(target.id)] = max(0.0, structured.agent_power.get(str(target.id), 0.5) - 0.2)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor="Unknown", action="exploit_vulnerability", target=target.name,
                outcome=f"{target.name} suffered a catastrophic internal failure", visibility=0.2
            ))
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=True, outcome=f"{agent.name} covertly exploited {target.name}'s vulnerability.",
                impact={"target_resources": -0.25, "target_power": -0.2}, affected_agents=[target.id], world_state_changes=structured.to_dict()
            )
        else:
            # FAILURE: Real consequences — exposure, resource cost, retaliation
            structured.agent_exposure[str(agent.id)] = min(1.0,
                structured.agent_exposure.get(str(agent.id), 0.0) + 0.35)
            structured.agent_resources[str(agent.id)] = max(0.02,
                structured.agent_resources.get(str(agent.id), 0.5) - 0.1)
            structured.agent_reputation[str(agent.id)] = max(0.0,
                structured.agent_reputation.get(str(agent.id), 0.5) - 0.1)

            # Create rivalry if not existing
            agent_id_str = str(agent.id)
            target_id_str = str(target.id)
            existing_rivalry = any(
                {r.agent_a, r.agent_b} == {agent_id_str, target_id_str}
                for r in structured.rivalries
            )
            if not existing_rivalry:
                structured.rivalries.append(RivalryRecord(
                    agent_a=target_id_str,
                    agent_b=agent_id_str,
                    started_at_step=simulation_step,
                    intensity=0.6,
                    cause="failed_exploit_attempt",
                ))

            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="exploit_vulnerability_failed",
                target=target.name,
                outcome=f"{agent.name}'s attempt to exploit {target.name}'s vulnerability was detected!",
                visibility=0.7,
            ))

            self._save_structured_state(world_state, structured)

            # Relationship damage
            rel_manager = RelationshipManager(target.id)
            await rel_manager.record_interaction(
                db,
                project_id=world_state.project_id if world_state else agent.id,
                other_agent_id=agent.id,
                interaction_type="betrayal",
                description=f"Caught {agent.name} trying to exploit our vulnerability",
                outcome="negative",
                trust_change=-0.6,
                strength_change=-0.4,
            )

            # Memory on target
            target_memory = AgentMemoryManager(target.id)
            await target_memory.remember(
                db,
                memory_type="discovery",
                content=f"{agent.name} tried to exploit our vulnerability — we caught them",
                importance=0.9,
                emotional_valence=-0.8,
                related_agents=[agent.id],
            )

            # Memory on actor
            actor_memory = AgentMemoryManager(agent.id)
            await actor_memory.remember(
                db,
                memory_type="decision",
                content=f"My exploit attempt on {target.name} failed — I was detected and exposed",
                importance=0.85,
                emotional_valence=-0.6,
                related_agents=[target.id],
            )

            # Psychology mutation
            psych_dict = agent.mutable_psychology or {}
            from backend.models.agent_models import MutablePsychology
            psych = MutablePsychology(**psych_dict) if psych_dict else MutablePsychology()
            psych.paranoia = min(1.0, psych.paranoia + 0.1)
            psych.fear = min(1.0, psych.fear + 0.1)
            agent.mutable_psychology = psych.model_dump()
            db.add(agent)

            logger.warning(f"✗ Exploit vulnerability FAILED: {agent.name} → {target.name}")

            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s attempt to exploit {target.name}'s vulnerability was detected!",
                impact={"exposure": 0.35, "resources": -0.1, "reputation": -0.1},
                affected_agents=[target.id],
                side_effects=[
                    "Exploit attempt detected",
                    "Agent exposed",
                    f"{target.name} now hostile",
                    "Retaliation likely",
                ],
                world_state_changes=structured.to_dict(),
            )



    async def execute_leak_secrets(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="rival")
        if not target:
            return ActionExecutionResult(success=False, outcome="No target found for leak.", impact={})
            
        structured = self._get_structured_state(world_state)
        if success:
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor="Anonymous", action="leak_secrets", target=target.name,
                outcome=f"Devastating internal secrets about {target.name} leaked to the public", visibility=1.0
            ))
            
            # Spread Misinformation/Belief covertly
            from backend.systems.trust_system import TrustMisinformationSystem
            trust_system = TrustMisinformationSystem()
            topic = f"{target.name} has devastating secrets"
            # Lower visibility but high target confidence
            await trust_system.spread_belief(db, agent.project_id, agent, topic, target_confidence=0.95, visibility=0.5)
            
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=True, outcome=f"{agent.name} anonymously leaked {target.name}'s secrets, swaying beliefs covertly.",
                impact={}, affected_agents=[target.id], world_state_changes=structured.to_dict()
            )
        else:
            # Failure: Use contextual consequence engine
            ctx = await self.contextual_engine.build_context(db, agent, target, structured)
            outcome, description = self.contextual_engine.resolve_failure(
                "leak", agent, target, ctx
            )
            await self.contextual_engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step, world_state
            )
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False, outcome=description,
                impact={"reputation": outcome.actor_reputation_delta, "exposure": outcome.actor_exposure_delta},
                affected_agents=[target.id], world_state_changes=structured.to_dict()
            )

    async def execute_defensive_restructuring(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        structured = self._get_structured_state(world_state)
        if success:
            structured.agent_exposure[str(agent.id)] = 0.0
            structured.agent_resources[str(agent.id)] = max(0.02, structured.agent_resources.get(str(agent.id), 0.5) - 0.15)
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step, actor=agent.name, action="defensive_restructuring", target="Self",
                outcome=f"{agent.name} underwent a massive defensive restructuring", visibility=0.8
            ))
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=True, outcome=f"{agent.name} cleared all exposure via restructuring.",
                impact={"exposure": -1.0, "resources": -0.15}, world_state_changes=structured.to_dict()
            )
        else:
            structured.agent_resources[str(agent.id)] = max(0.02, structured.agent_resources.get(str(agent.id), 0.5) - 0.15)
            self._save_structured_state(world_state, structured)
            return ActionExecutionResult(
                success=False, outcome=f"{agent.name}'s restructuring failed, wasting resources.", impact={"resources": -0.15},
                world_state_changes=structured.to_dict()
            )

    async def execute_betrayal(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Betrayal — break trust with a target, especially an ally.

        Rules:
        - Target selected from decision context; preference is "ally" (betrayal hurts most)
        - On success: massive trust damage, alliance dissolved, target weakened,
          agent gains short-term power but long-term reputation risk
        - On failure: contextual consequences via ContextualConsequenceEngine
          (blackmail, social isolation, secret exposure, faction fracture, etc.)
        """
        target = await self._resolve_target_agent(db, agent, decision, preference="ally")

        if not target:
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name} could not find a target to betray",
                impact={},
                side_effects=["No suitable target found"],
            )

        structured = self._get_structured_state(world_state)
        agent_id_str = str(agent.id)
        target_id_str = str(target.id)

        if success:
            # ── SUCCESS: Target is devastated ──

            # Dissolve any alliance
            structured.alliances = [
                a for a in structured.alliances
                if not ({a.agent_a, a.agent_b} == {agent_id_str, target_id_str})
            ]

            # Damage target
            structured.agent_resources[target_id_str] = max(0.02,
                structured.agent_resources.get(target_id_str, 0.5) - 0.25)
            structured.agent_power[target_id_str] = max(0.0,
                structured.agent_power.get(target_id_str, 0.5) - 0.2)

            # Agent gains short-term power from exploiting trust
            structured.agent_power[agent_id_str] = min(1.0,
                structured.agent_power.get(agent_id_str, 0.5) + 0.15)
            structured.agent_resources[agent_id_str] = min(1.0,
                structured.agent_resources.get(agent_id_str, 0.5) + 0.1)

            # Create intense rivalry
            existing_rivalry = any(
                {r.agent_a, r.agent_b} == {agent_id_str, target_id_str}
                for r in structured.rivalries
            )
            if not existing_rivalry:
                structured.rivalries.append(RivalryRecord(
                    agent_a=target_id_str,
                    agent_b=agent_id_str,
                    started_at_step=simulation_step,
                    intensity=0.95,
                    cause="betrayal",
                ))

            # High-visibility event
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="betrayal",
                target=target.name,
                outcome=f"{agent.name} betrayed {target.name}, shattering their trust!",
                visibility=0.9,
            ))

            self._save_structured_state(world_state, structured)

            # Destroy trust in the relationship
            rel_manager = RelationshipManager(target.id)
            await rel_manager.record_interaction(
                db,
                project_id=world_state.project_id if world_state else agent.project_id,
                other_agent_id=agent.id,
                interaction_type="betrayal",
                description=f"{agent.name} betrayed {target.name}",
                outcome="negative",
                trust_change=-1.0,
                strength_change=-1.0,
            )

            # Record devastating memory on target
            target_memory = AgentMemoryManager(target.id)
            await target_memory.remember(
                db,
                memory_type="discovery",
                content=f"{agent.name} betrayed me — they exploited our trust and alliance",
                importance=0.98,
                emotional_valence=-0.95,
                related_agents=[agent.id],
            )

            # Record on actor
            actor_memory = AgentMemoryManager(agent.id)
            await actor_memory.remember(
                db,
                memory_type="decision",
                content=f"I betrayed {target.name} — gained power but burned bridges",
                importance=0.85,
                emotional_valence=-0.3,
                related_agents=[target.id],
            )

            # Mutate actor psychology: betrayal increases paranoia
            psych_dict = agent.mutable_psychology or {}
            from backend.models.agent_models import MutablePsychology
            psych = MutablePsychology(**psych_dict) if psych_dict else MutablePsychology()
            psych.paranoia = min(1.0, psych.paranoia + 0.15)
            psych.betrayal_wounds += 1  # actor tracks their own betrayals
            agent.mutable_psychology = psych.model_dump()
            db.add(agent)

            logger.info(f"✓ Betrayal successful: {agent.name} → {target.name}")

            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} betrayed {target.name}, shattering their alliance and seizing power!",
                impact={"power": 0.15, "resources": 0.1, "target_resources": -0.25},
                affected_agents=[target.id],
                side_effects=[
                    f"{target.name} devastated — trust destroyed",
                    "Alliance dissolved",
                    "Intense rivalry created",
                    "Long-term reputation risk",
                ],
                world_state_changes=structured.to_dict(),
            )
        else:
            # ── FAILURE: Use contextual consequence engine ──
            ctx = await self.contextual_engine.build_context(db, agent, target, structured)
            outcome, description = self.contextual_engine.resolve_failure(
                "betrayal", agent, target, ctx
            )
            await self.contextual_engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step, world_state
            )

            self._save_structured_state(world_state, structured)

            logger.warning(f"✗ Betrayal FAILED: {agent.name} → {target.name} [{outcome.key}]")

            return ActionExecutionResult(
                success=False,
                outcome=description,
                impact={
                    "reputation": outcome.actor_reputation_delta,
                    "exposure": outcome.actor_exposure_delta,
                    "power": outcome.actor_power_delta,
                },
                affected_agents=[target.id],
                side_effects=[
                    f"Consequence: {outcome.key}",
                    f"{target.name}'s trust destroyed" if outcome.target_trust_delta < -0.5 else "Trust damaged",
                    "Retaliation expected" if outcome.creates_rivalry else "Situation volatile",
                ],
                world_state_changes=structured.to_dict(),
            )

    async def execute_build_relationship(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional['WorldState'],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        target = await self._resolve_target_agent(db, agent, decision, preference="ally")
        if not target:
            return ActionExecutionResult(success=False, outcome="No target found to build relationship.", impact={})
            
        structured = self._get_structured_state(world_state)
        
        # Create a proposal instead of immediate execution
        proposal = {
            "id": str(uuid4()),
            "type": "relationship",
            "from_agent_id": str(agent.id),
            "from_agent_name": agent.name,
            "to_agent_id": str(target.id),
            "to_agent_name": target.name,
            "step_created": simulation_step,
            "context": decision.reasoning
        }
        structured.pending_proposals.append(proposal)
        self._save_structured_state(world_state, structured)
        
        return ActionExecutionResult(
            success=True, 
            outcome=f"{agent.name} sent a relationship proposal to {target.name}.", 
            impact={}, 
            world_state_changes=structured.to_dict()
        )

    async def execute_action(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Route action to appropriate executor based on action type.
        
        This is the main entry point for executing actions.
        """
        action_type = decision.action.lower()
        
        # Map action strings to executor methods
        if action_type == "gather_intel":
            return await self.execute_gather_intel(db, agent, decision, world_state, simulation_step, success)

        
        elif "contract" in action_type or "bid" in action_type:
            return await self.execute_contract_bid(db, agent, decision, world_state, simulation_step, success)
        
        elif "lobby" in action_type or "influencer" in action_type:
            return await self.execute_lobbying(db, agent, decision, world_state, simulation_step, success)
            
        elif "legal" in action_type or "lawsuit" in action_type or "court" in action_type:
            return await self.execute_legal_action(db, agent, decision, world_state, simulation_step, success)
            
        elif "media" in action_type or "press" in action_type or "journal" in action_type:
            return await self.execute_media_campaign(db, agent, decision, world_state, simulation_step, success)
            
        elif "hostile" in action_type and "takeover" in action_type:
            return await self.execute_hostile_takeover(db, agent, decision, world_state, simulation_step, success)
            
        elif "poach" in action_type or ("hire" in action_type and "talent" in action_type):
            return await self.execute_poach_talent(db, agent, decision, world_state, simulation_step, success)
            
        elif "exploit" in action_type or "vulnerabil" in action_type:
            return await self.execute_exploit_vulnerability(db, agent, decision, world_state, simulation_step, success)
            

            
        elif "leak" in action_type or "secret" in action_type:
            return await self.execute_leak_secrets(db, agent, decision, world_state, simulation_step, success)
            
        elif "defensive" in action_type or "restructur" in action_type:
            return await self.execute_defensive_restructuring(db, agent, decision, world_state, simulation_step, success)
        
        elif "betray" in action_type:
            return await self.execute_betrayal(db, agent, decision, world_state, simulation_step, success)
        
        elif "sabotage" in action_type or "infiltrate" in action_type:
            return await self.execute_sabotage(db, agent, decision, world_state, simulation_step, success)
        
        elif "campaign" in action_type or "protest" in action_type or "expose" in action_type or "movement" in action_type or "ideology" in action_type:
            return await self.execute_campaign(db, agent, decision, world_state, simulation_step, success)
        
        elif "attack" in action_type or "assault" in action_type or "war" in action_type or "revenge" in action_type:
            return await self.execute_attack(db, agent, decision, world_state, simulation_step, success)
        
        elif "expand" in action_type or "grow" in action_type or "launch" in action_type or "product" in action_type:
            return await self.execute_expansion(db, agent, decision, world_state, simulation_step, success)
        
        elif "acqui" in action_type or "takeover" in action_type or "buyout" in action_type:
            return await self.execute_acquisition(db, agent, decision, world_state, simulation_step, success)
        
        elif "negotiat" in action_type or "deal" in action_type or "treaty" in action_type:
            return await self.execute_negotiation(db, agent, decision, world_state, simulation_step, success)
        
        elif "invest" in action_type or "r&d" in action_type or "innovation" in action_type or "innovate" in action_type or "research" in action_type:
            return await self.execute_investment(db, agent, decision, world_state, simulation_step, success)
        
        elif "policy" in action_type or "regulat" in action_type or "law" in action_type or "sanction" in action_type:
            return await self.execute_policy(db, agent, decision, world_state, simulation_step, success)
        
        elif "hire" in action_type or "recruit" in action_type or "poach" in action_type or "talent" in action_type:
            return await self.execute_talent(db, agent, decision, world_state, simulation_step, success)
        
        else:
            # Generic fallback for unrecognized actions (observe, wait, help others, trade)
            return await self.execute_generic(db, agent, decision, world_state, simulation_step, success)

    async def execute_generic(
        self,
        db: AsyncSession,
        agent: Agent,
        decision: AgentDecision,
        world_state: Optional[WorldState],
        simulation_step: int,
        success: bool,
    ) -> ActionExecutionResult:
        """
        Generic executor for actions that don't have specific handlers.
        Provides basic success/failure outcomes.
        """
        structured = self._get_structured_state(world_state)
        
        if success:
            # Generic success: small resource/power gain
            structured.agent_resources[str(agent.id)] = min(1.0,
                structured.agent_resources.get(str(agent.id), 0.5) + 0.08)
            
            structured.recent_events.append(WorldEventRecord(
                step=simulation_step,
                actor=agent.name,
                action="generic_action",
                outcome=f"{agent.name}: {decision.action}",
                visibility=0.3,
            ))
            
            self._save_structured_state(world_state, structured)
            
            logger.info(f"✓ Generic action successful: {agent.name} - {decision.action}")
            
            return ActionExecutionResult(
                success=True,
                outcome=f"{agent.name} successfully executed: {decision.action}",
                public_impact=decision.action.lower() not in ["gather_intel"],
                impact={"resources": 0.08},
                side_effects=["Action completed"],
                world_state_changes=structured.to_dict(),
            )
        else:
            # Generic failure: small resource loss
            structured.agent_resources[str(agent.id)] = max(0.02,
                structured.agent_resources.get(str(agent.id), 0.5) - 0.05)
            
            self._save_structured_state(world_state, structured)
            
            logger.warning(f"✗ Generic action failed: {agent.name} - {decision.action}")
            
            return ActionExecutionResult(
                success=False,
                outcome=f"{agent.name}'s action failed: {decision.action}",
                impact={"resources": -0.05},
                side_effects=["Action failed"],
                world_state_changes=structured.to_dict(),
            )
