"""
MapR1 — Consequence Engine (Phase 2)

Runs after all agent actions in a step to propagate consequences:
- Retaliation motivation for attacked/sabotaged agents
- Event visibility decay over time
- Compound effects (campaign tipping points)
- Alliance decay
- Regulatory triggers
"""

from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.action_models import ActionResponse
from backend.models.world_models import WorldState, StructuredWorldState, WorldEventRecord
from backend.agents.agent_memory import AgentMemoryManager
from backend.systems.delayed_effect_system import DelayedEffectSystem


class ConsequenceEngine:
    """
    Propagates consequences after all agents have acted in a step.
    """

    async def propagate(
        self,
        db: AsyncSession,
        world_state: WorldState,
        actions_this_step: List[ActionResponse],
        current_step: int,
    ) -> List[WorldEventRecord]:
        """
        Process all consequences from this step's actions.
        Returns list of new consequential events to add to world state.
        """
        structured = self._get_structured_state(world_state)
        new_events = []
        
        logger.info(f"Propagating consequences for step {current_step}...")
        
        # 0. Filter out events for private actions
        private_agents = {a.agent_name for a in actions_this_step if not getattr(a, "public_impact", True)}
        structured.recent_events = [
            e for e in structured.recent_events
            if not (e.step == current_step and e.actor in private_agents)
        ]
        
        # 1. Retaliation motivation
        retaliation_count = await self._inject_retaliation_motivations(
            db, actions_this_step, current_step
        )
        if retaliation_count > 0:
            logger.debug(f"  Injected {retaliation_count} retaliation motivations")
        
        # 2. Decay old events (reduce visibility by 0.1 per step)
        for event in structured.recent_events:
            event.visibility = max(0, event.visibility - 0.1)
        
        # Remove events older than 10 steps
        old_count = len(structured.recent_events)
        structured.recent_events = [
            e for e in structured.recent_events 
            if current_step - e.step < 10
        ]
        removed = old_count - len(structured.recent_events)
        if removed > 0:
            logger.debug(f"  Removed {removed} old events")
        
        # 3. Compound campaign effects — tipping point
        tipping_events = self._check_campaign_tipping_points(structured, current_step)
        new_events.extend(tipping_events)
        if tipping_events:
            logger.info(f"  {len(tipping_events)} campaign tipping points reached!")
        
        # 4. Alliance decay — alliances lose 0.05 strength per step if no interaction
        decayed = 0
        for alliance in structured.alliances:
            alliance.strength = max(0.1, alliance.strength - 0.05)
            if alliance.strength <= 0.1:
                decayed += 1
        
        # Remove dead alliances
        structured.alliances = [a for a in structured.alliances if a.strength > 0.1]
        if decayed > 0:
            logger.debug(f"  {decayed} alliances decayed")
        
        # 5. Regulatory pressure effects
        regulatory_events = self._check_regulatory_triggers(structured, current_step)
        new_events.extend(regulatory_events)
        if regulatory_events:
            logger.info(f"  {len(regulatory_events)} regulatory actions triggered!")
        
        # Add new events to world state
        structured.recent_events.extend(new_events)
        self._save_structured_state(world_state, structured)
        
        # 6. Schedule Delayed Consequences
        import random
        delayed_system = DelayedEffectSystem()
        
        # Determine remaining steps to bound the delay
        total_steps = structured.metadata.get("suggested_steps", 10) if structured.metadata else 10
        remaining_steps = max(1, total_steps - current_step)
        
        for action in actions_this_step:
            action_type_lower = action.action_type.lower()
            if action.success and ("cut_safety_testing" in action_type_lower or "risky_research" in action_type_lower):
                # Delay between 1 and 5, but guaranteed to fire before the simulation ends (if possible)
                delay = random.randint(1, min(5, remaining_steps))
                await delayed_system.schedule(
                    db=db,
                    project_id=world_state.project_id,
                    trigger_turn=current_step + delay,
                    event_type="regulatory_backlash",
                    description=f"Regulatory backlash triggered by {action.agent_name}'s safety cuts.",
                    impact_data={"regulatory_pressure": {"industry": 0.4}},
                    cause_action_id=action.id,
                )
        
        logger.info(f"Consequence propagation complete: {len(new_events)} new events generated")
        
        return new_events

    async def _inject_retaliation_motivations(
        self,
        db: AsyncSession,
        actions: List[ActionResponse],
        step: int,
    ) -> int:
        """
        Give victims of attacks/sabotage a strong memory motivating retaliation.
        Returns count of motivations injected.
        """
        count = 0
        
        for action in actions:
            # Check if this was an attack or sabotage that succeeded
            if action.action_type.lower() in ["attack", "sabotage"] and action.success:
                # Find the target agent ID from affected_agents
                if action.impact and "affected_agents" in action.impact:
                    target_ids = action.impact["affected_agents"]
                    
                    for target_id in target_ids:
                        try:
                            memory_mgr = AgentMemoryManager(UUID(target_id))
                            await memory_mgr.remember(
                                db,
                                memory_type="discovery",
                                content=f"I was {action.action_type} by {action.agent_name} in step {step}. I need to respond.",
                                importance=0.95,
                                emotional_valence=-0.9,
                            )
                            count += 1
                        except Exception as e:
                            logger.error(f"Failed to inject retaliation motivation: {e}")
        
        return count

    def _check_campaign_tipping_points(
        self,
        structured: StructuredWorldState,
        current_step: int,
    ) -> List[WorldEventRecord]:
        """
        Check if any campaigns have reached tipping points.
        Returns list of consequential events.
        """
        events = []
        
        for topic, opinion in structured.public_opinion.items():
            if opinion > 0.8:
                # Tipping point reached — check if media attention is also high
                media = structured.media_attention.get(topic, 0)
                if media > 0.7:
                    # Extract target entity from topic (e.g., "techcorp_environment" -> "techcorp")
                    target = topic.split("_")[0] if "_" in topic else "industry"
                    
                    events.append(WorldEventRecord(
                        step=current_step,
                        actor="regulatory_body",
                        action="investigation_launched",
                        target=target,
                        outcome=f"Regulatory investigation launched into {target} after sustained public pressure on {topic}",
                        visibility=1.0,
                    ))
                    
                    # Increase regulatory pressure
                    structured.regulatory_pressure[target] = min(1.0,
                        structured.regulatory_pressure.get(target, 0.0) + 0.4)
        
        return events

    def _check_regulatory_triggers(
        self,
        structured: StructuredWorldState,
        current_step: int,
    ) -> List[WorldEventRecord]:
        """
        Check if regulatory pressure has triggered enforcement actions.
        Returns list of consequential events.
        """
        events = []
        
        for entity, pressure in list(structured.regulatory_pressure.items()):
            if pressure > 0.9:
                events.append(WorldEventRecord(
                    step=current_step,
                    actor="regulatory_body",
                    action="enforcement_action",
                    target=entity,
                    outcome=f"Regulatory enforcement action taken against {entity}",
                    visibility=1.0,
                ))
                
                # Reset pressure after enforcement
                structured.regulatory_pressure[entity] = 0.3
        
        return events

    def _get_structured_state(self, world_state: WorldState) -> StructuredWorldState:
        """Get or create structured world state"""
        if not world_state or not world_state.state:
            return StructuredWorldState()
        
        if isinstance(world_state.state, dict) and "agent_resources" in world_state.state:
            return StructuredWorldState.from_dict(world_state.state)
        
        return StructuredWorldState.from_legacy_state(world_state.state)

    def _save_structured_state(self, world_state: WorldState, structured: StructuredWorldState):
        """Save structured state back to WorldState object"""
        if world_state:
            world_state.state = structured.to_dict()
