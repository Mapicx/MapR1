"""
MapR1 — Goal Weaver (Pass 4)

Assigns goals and seeds hidden knowledge for each agent.
Goals should CONFLICT, and hidden facts should be ACTIONABLE.
"""

from typing import List, Tuple, Optional
from loguru import logger
from backend.seeder.seed_models import (
    ScenarioDNA,
    AgentSeed,
    EntitySeed,
    GoalSeed,
    HiddenFactSeed,
)
from backend.seeder.openrouter_client import openrouter_client
from pydantic import BaseModel

class GoalWeaverResponse(BaseModel):
    goals: List[GoalSeed]
    hidden_facts: List[HiddenFactSeed]


GOAL_WEAVING_SYSTEM_PROMPT = """You are a goal architect for MapR1 simulations.

Your job is to assign goals to agents and seed hidden facts that agents can discover during the simulation.

**CRITICAL RULES FOR GOALS**:
1. Each agent gets 1-3 goals
2. Goals should CONFLICT — CEO A's goal should threaten CEO B's
3. Goal types MUST strictly be one of the provided victory or failure condition keys
4. Priority: 0.0-1.0 (how important this goal is to the agent)
5. List which other agents' goals this conflicts with

**CRITICAL RULES FOR HIDDEN FACTS**:
1. Hidden facts are discoverable during the "gather_information" phase
2. Facts should be ACTIONABLE — discovering them enables new actions
3. Facts should be scenario-specific (not generic)
4. Discoverable by: agent types (e.g., ["role_0"]) or "*" for anyone
5. Discovery context: investigation, whistleblower, leaked_document, insider_tip, etc.
6. Each fact should enable a specific action

Return valid JSON matching this schema:
{
  "goals": [
    {
      "agent_name": "string",
      "description": "string (what the agent wants to achieve)",
      "goal_type": "string (victory_key or failure_key from the available list)",
      "priority": float (0.0-1.0),
      "conflicts_with": ["agent_name1", "agent_name2"]
    }
  ],
  "hidden_facts": [
    {
      "fact": "string (the discoverable fact)",
      "discoverable_by": ["role_key" or "*"],
      "discovery_context": "string (investigation/whistleblower/etc.)",
      "goal_relevance": "string (which goal type this helps with)",
      "action_it_enables": "string (what action this unlocks)"
    }
  ]
}"""


class GoalWeaver:
    """Weaves goals and hidden knowledge into the scenario."""
    
    async def weave(
        self,
        dna: ScenarioDNA,
        agents: List[AgentSeed],
        entities: List[EntitySeed],
        victory_conditions: dict[str, str] = None,
        failure_conditions: dict[str, str] = None,
        user_overrides: Optional[dict] = None,
    ) -> Tuple[List[GoalSeed], List[HiddenFactSeed]]:
        """
        Generate goals and hidden facts for agents.
        
        Args:
            dna: Scenario DNA
            agents: Cast agents
            entities: Generated entities
            victory_conditions: Valid victory keys from active theme
            failure_conditions: Valid failure keys from active theme
            user_overrides: Optional user-specified overrides
        
        Returns:
            Tuple of (goals, hidden_facts)
        """
        logger.info(f"Weaving goals and hidden knowledge for '{dna.title}'...")
        
        # Build agent descriptions
        agent_descriptions = []
        for agent in agents:
            agent_descriptions.append(
                f"- **{agent.name}** ({agent.agent_type}, {agent.role}): "
                f"Faction: {agent.faction}. Function: {agent.dramatic_function}. "
                f"Backstory: {agent.backstory}"
            )
            
        victory_str = "\n".join([f"- {k}: {v}" for k, v in (victory_conditions or {}).items()])
        failure_str = "\n".join([f"- {k}: {v}" for k, v in (failure_conditions or {}).items()])
        
        user_prompt = f"""Generate goals and hidden facts for this scenario:

**Title**: {dna.title}
**Core Tension**: {dna.core_tension}
**Secondary Tensions**: {', '.join(dna.secondary_tensions)}

**Agents**:
{chr(10).join(agent_descriptions)}

**Key Variables**: {', '.join(dna.key_variables)}
**Potential Wildcards**: {', '.join(dna.potential_wildcards)}

**Available Victory Keys (use these for goal_type)**:
{victory_str}

**Available Failure Keys (use these for goal_type)**:
{failure_str}

Create conflicting goals that drive the narrative.
Seed hidden facts that are thematically relevant and actionable."""
        
        try:
            response = await openrouter_client.generate_structured(
                response_model=GoalWeaverResponse,
                prompt=user_prompt,
                system_prompt=GOAL_WEAVING_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=2500,
            )
            
            # Parse goals
            goals = response.goals
            
            # Parse hidden facts
            hidden_facts = response.hidden_facts
            
            # Apply user overrides if provided
            if user_overrides:
                if "goals" in user_overrides:
                    for goal_override in user_overrides["goals"]:
                        goals.append(GoalSeed(**goal_override))
                if "hidden_facts" in user_overrides:
                    for fact_override in user_overrides["hidden_facts"]:
                        hidden_facts.append(HiddenFactSeed(**fact_override))
            
            logger.success(
                f"✓ Wove {len(goals)} goals and seeded {len(hidden_facts)} hidden facts"
            )
            
            # Log goal conflicts
            conflict_count = sum(len(g.conflicts_with) for g in goals)
            logger.info(f"  Goal conflicts: {conflict_count}")
            
            return goals, hidden_facts
        
        except Exception as e:
            logger.error(f"Goal weaving failed: {e}")
            raise


# Global instance
goal_weaver = GoalWeaver()
