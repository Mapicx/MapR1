from typing import Tuple, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.belief_models import PublicBeliefState, AgentBeliefState
from backend.models.agent_models import Agent


class TrustMisinformationSystem:
    """
    Simulates belief, not truth. Belief drives action.
    Updates public belief and target agent beliefs based on source credibility and propaganda power.
    """

    async def spread_belief(
        self,
        db: AsyncSession,
        project_id: UUID,
        source_agent: Agent,
        topic: str,
        target_confidence: float,
        visibility: float = 1.0,
        target_agent_id: Optional[UUID] = None,
    ) -> None:
        """
        Agent injects a belief into the public or specifically to another agent.
        
        Args:
            source_agent: The agent spreading the information
            topic: The belief topic (e.g. "Entity_X_is_hoarding_Resource_Y")
            target_confidence: The confidence level (0.0 to 1.0) the source wants people to have
            visibility: 0.0 to 1.0 (1.0 = media campaign, 0.1 = whisper/leak)
            target_agent_id: If provided, targets a specific agent instead of the public
        """
        # Fetch the source agent's belief state to determine their credibility and propaganda power
        source_state = await self._get_or_create_agent_state(db, source_agent.id)
        
        # Power multiplier: How good are they at spreading info?
        effective_power = source_state.propaganda_power * source_state.credibility * visibility

        if target_agent_id:
            # Spread to a specific agent (e.g. leaking secrets directly)
            await self._modify_agent_belief(db, target_agent_id, source_agent.id, topic, target_confidence, effective_power)
        else:
            # Spread to public (e.g. media campaign)
            await self._modify_public_belief(db, project_id, source_agent.id, topic, target_confidence, effective_power)

    async def _modify_public_belief(
        self, db: AsyncSession, project_id: UUID, source_agent_id: UUID, topic: str, target_confidence: float, power: float
    ) -> None:
        public_state = await self._get_or_create_public_state(db, project_id)
        
        current_beliefs = dict(public_state.beliefs)
        current_conf = current_beliefs.get(topic, 0.5) # Default neutral
        
        # Calculate shift
        shift = (target_confidence - current_conf) * power
        new_conf = max(0.0, min(1.0, current_conf + shift))
        
        current_beliefs[topic] = new_conf
        public_state.beliefs = current_beliefs
        db.add(public_state)

    async def _modify_agent_belief(
        self, db: AsyncSession, target_agent_id: UUID, source_agent_id: UUID, topic: str, target_confidence: float, power: float
    ) -> None:
        target_state = await self._get_or_create_agent_state(db, target_agent_id)
        
        # Fetch target agent to get paranoia from mutable psychology
        target_agent = await db.get(Agent, target_agent_id)
        paranoia = 0.3
        if target_agent and target_agent.mutable_psychology:
            paranoia = target_agent.mutable_psychology.get("paranoia", 0.3)
        
        # If target doesn't trust the source, the power is reduced
        trust_map = target_state.trust_in_others or {}
        source_trust = trust_map.get(str(source_agent_id), 0.5)
        
        # Paranoia makes them less likely to change beliefs
        paranoia_factor = 1.0 - paranoia
        
        effective_shift_power = power * source_trust * paranoia_factor
        
        current_facts = dict(target_state.known_facts)
        
        # known_facts values are now dicts matching FactRecord {"confidence": x, "source": y, "step_learned": z}
        existing_fact = current_facts.get(topic, {})
        current_conf = existing_fact.get("confidence", 0.5) if isinstance(existing_fact, dict) else float(existing_fact) if existing_fact else 0.5
        
        shift = (target_confidence - current_conf) * effective_shift_power
        new_conf = max(0.0, min(1.0, current_conf + shift))
        
        current_facts[topic] = {
            "confidence": new_conf,
            "source": f"agent_{source_agent_id}",
            "step_learned": 0 # This could be updated if we pass the current step to this function
        }
        target_state.known_facts = current_facts
        db.add(target_state)

    async def _get_or_create_public_state(self, db: AsyncSession, project_id: UUID) -> PublicBeliefState:
        result = await db.execute(select(PublicBeliefState).where(PublicBeliefState.project_id == project_id))
        state = result.scalar_one_or_none()
        if not state:
            state = PublicBeliefState(project_id=project_id, beliefs={}, source_to_trust={})
            db.add(state)
        return state

    async def _get_or_create_agent_state(self, db: AsyncSession, agent_id: UUID) -> AgentBeliefState:
        result = await db.execute(select(AgentBeliefState).where(AgentBeliefState.agent_id == agent_id))
        state = result.scalar_one_or_none()
        if not state:
            state = AgentBeliefState(
                agent_id=agent_id, 
                known_facts={}, 
                trust_in_others={},
                propaganda_power=0.5,
                credibility=0.5
            )
            db.add(state)
        return state

    async def get_public_beliefs(self, db: AsyncSession, project_id: UUID) -> Dict[str, float]:
        state = await self._get_or_create_public_state(db, project_id)
        return state.beliefs or {}

    async def get_agent_beliefs(self, db: AsyncSession, agent_id: UUID) -> Dict[str, Dict[str, Any]]:
        state = await self._get_or_create_agent_state(db, agent_id)
        return state.known_facts or {}
