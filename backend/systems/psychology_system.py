from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.agent_models import Agent, MutablePsychology
from backend.models.world_models import StructuredWorldState
from backend.models.action_models import ActionExecutionResult

class PsychologySystem:
    """
    Manages the mutable psychological traits of agents over time.
    Shifts baseline traits based on outcomes, consequences, and environment.
    """

    async def update_agent_psychology(
        self,
        db: AsyncSession,
        agent: Agent,
        action_type: str,
        exec_result: ActionExecutionResult,
        structured_world: StructuredWorldState
    ) -> None:
        """
        Evolves agent psychology based on action outcomes and world context.
        """
        # Load or create psychology
        psych_dict = agent.mutable_psychology or {}
        psych = MutablePsychology(**psych_dict)

        # 1. Evaluate Success/Failure
        if not exec_result.success:
            psych.consecutive_failures += 1
            psych.fear = min(1.0, psych.fear + 0.1)
            psych.paranoia = min(1.0, psych.paranoia + 0.08)
            
            # Repeated failures radicalize
            if psych.consecutive_failures >= 3:
                psych.radicalization = min(1.0, psych.radicalization + 0.3)
                psych.paranoia = min(1.0, psych.paranoia + 0.2)
        else:
            # Success resets consecutive failures and slightly boosts ego
            psych.consecutive_failures = 0
            psych.ego = min(1.0, psych.ego + 0.05)
            psych.fear = max(0.0, psych.fear - 0.05)

        # 2. Evaluate Betrayal
        if action_type == "betrayal":
            psych.idealism = max(0.0, psych.idealism - 0.2)
            psych.risk_tolerance = min(1.0, psych.risk_tolerance + 0.1)
            # If the agent is betraying someone, it also increases paranoia (looking over their shoulder)
            psych.paranoia = min(1.0, psych.paranoia + 0.1)

        # Note: If the agent is the TARGET of a betrayal, that would ideally be handled
        # when the action happens, but the actor's update is a good start. For targeted betrayals,
        # we can detect it if the outcome indicates betrayal, but we'll stick to action_type for now.

        # 3. Resource Scarcity
        agent_id_str = str(agent.id)
        current_resources = structured_world.agent_resources.get(agent_id_str, 1.0)
        
        if current_resources < 0.3:
            psych.greed = min(1.0, psych.greed + 0.15)
            psych.desperation = min(1.0, psych.desperation + 0.2)
            psych.fear = min(1.0, psych.fear + 0.1)
        elif current_resources > 0.8:
            # Wealth reduces desperation but might boost ego or greed slightly
            psych.desperation = max(0.0, psych.desperation - 0.1)
            psych.ego = min(1.0, psych.ego + 0.05)

        # 4. Exposure
        current_exposure = structured_world.agent_exposure.get(agent_id_str, 0.0)
        if current_exposure > 0.6:
            psych.paranoia = min(1.0, psych.paranoia + 0.1)

        # Save back to agent
        agent.mutable_psychology = psych.model_dump()
        db.add(agent)
