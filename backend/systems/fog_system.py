from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.belief_models import AgentBeliefState
from backend.models.agent_models import Agent
from backend.systems.trust_system import TrustMisinformationSystem

import random

class FogOfWarSystem:
    """
    Handles what agents can perceive. Replaces omniscient global state reading.
    When an action occurs, this system decides which agents observe it,
    and then writes that observation into their belief state via the Trust System.
    """
    def __init__(self):
        self.trust_system = TrustMisinformationSystem()

    async def broadcast_event(
        self,
        db: AsyncSession,
        project_id: UUID,
        actor_name: str,
        target_name: Optional[str],
        outcome: str,
        base_visibility: float,
        actor_exposure: float,
        all_agents: List[Agent],
        current_step: int
    ) -> None:
        """
        Calculates who observed a newly executed action/event, and records it as a fact for them.
        """
        for agent in all_agents:
            # You always know what you did, or what was done directly to you
            if actor_name == agent.name or target_name == agent.name:
                await self._reveal_fact(db, project_id, agent, outcome, actor_name, 1.0, current_step)
                continue
                
            # Otherwise, observation check
            obviousness = (base_visibility + actor_exposure) / 2.0
            
            # Simple probabilistic check for now
            if random.random() < obviousness:
                confidence = max(0.5, min(1.0, obviousness + 0.2))
                await self._reveal_fact(db, project_id, agent, outcome, actor_name, confidence, current_step)


    async def _reveal_fact(
        self,
        db: AsyncSession,
        project_id: UUID,
        agent: Agent,
        topic: str,
        actor_name: str,
        confidence: float,
        current_step: int
    ) -> None:
        """
        Directly injects the event into the agent's known_facts dictionary.
        """
        state = await self._get_or_create_agent_state(db, agent.id)
        current_facts = dict(state.known_facts)
        
        current_facts[topic] = {
            "confidence": confidence,
            "source": "observation" if actor_name != agent.name else "direct_experience",
            "step_learned": current_step
        }
        
        state.known_facts = current_facts
        db.add(state)

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
