"""
Pattern Detector

Uses LLM to detect emergent patterns in simulation with full context.
Analyzes entities, agents, scenarios, events, relationships, and actions.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from pydantic import BaseModel, Field

from backend.models.llm_client import ollama_client
from backend.models.action_models import EmergentPattern, AgentAction
from backend.models.agent_models import Agent
from backend.models.entity_models import Entity
from backend.models.db_models import DBScenario, DBTimelineEvent
from backend.models.world_models import WorldEvent, WorldState
from backend.models.relationship_models import AgentRelationship, AgentInteraction
from backend.models.goal_models import Goal
from backend.repositories.timeline_repository import TimelineRepository


class DetectedPattern(BaseModel):
    """A pattern detected by the LLM"""
    pattern_type: str = Field(..., description="Type of pattern (alliance_formation, conflict_escalation, etc.)")
    title: str = Field(..., description="Short title for the pattern")
    description: str = Field(..., description="Detailed description of what's happening")
    significance: float = Field(..., ge=0.0, le=1.0, description="How significant is this pattern (0-1)")
    involved_agents: List[str] = Field(default_factory=list, description="Agent names involved")
    involved_entities: List[str] = Field(default_factory=list, description="Entity names involved")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")


class PatternAnalysis(BaseModel):
    """Complete pattern analysis from LLM"""
    patterns: List[DetectedPattern] = Field(default_factory=list)
    overall_trends: str = Field(..., description="Overall trends in the simulation")
    predictions: List[str] = Field(default_factory=list, description="Predictions for future developments")


class PatternDetector:
    """Detects emergent patterns using LLM with full simulation context"""
    
    def __init__(self):
        self.llm = ollama_client
    
    async def detect_patterns(
        self,
        db: AsyncSession,
        project_id: UUID,
        time_window: int = 10,
        min_significance: float = 0.5,
    ) -> List[EmergentPattern]:
        """
        Detect emergent patterns using LLM with comprehensive context.
        
        Gathers full context:
        - All entities in the project
        - All agents and their goals
        - All scenarios and timeline events
        - Recent actions and world events
        - All relationships and interactions
        
        Args:
            project_id: Project to analyze
            time_window: Number of recent steps to analyze
            min_significance: Minimum significance threshold
        
        Returns:
            List of detected EmergentPattern objects
        """
        logger.info(f"Detecting patterns for project {project_id} (window: {time_window} steps)")
        
        # Gather comprehensive context
        context = await self._gather_full_context(db, project_id, time_window)
        
        # Build pattern detection prompt
        prompt = self._build_pattern_prompt(context)
        
        logger.debug(f"Pattern detection prompt length: {len(prompt)} characters")
        
        # Ask LLM to analyze
        try:
            analysis = await self.llm.generate_structured(
                prompt=prompt,
                response_model=PatternAnalysis,
            )
            
            logger.info(f"LLM detected {len(analysis.patterns)} patterns")
            
            # Convert to database models and save
            patterns = []
            for detected in analysis.patterns:
                if detected.significance >= min_significance:
                    pattern = await self._save_pattern(
                        db, project_id, detected, context
                    )
                    patterns.append(pattern)
            
            logger.info(f"Saved {len(patterns)} significant patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to detect patterns: {e}")
            return []
    
    async def _gather_full_context(
        self,
        db: AsyncSession,
        project_id: UUID,
        time_window: int,
    ) -> Dict[str, Any]:
        """Gather comprehensive simulation context"""
        logger.debug("Gathering full simulation context...")
        
        context = {
            "project_id": project_id,
            "entities": [],
            "agents": [],
            "scenarios": [],
            "timeline_events": [],
            "world_events": [],
            "actions": [],
            "relationships": [],
            "interactions": [],
            "goals": [],
        }
        
        # Get all entities
        result = await db.execute(
            select(Entity).where(Entity.project_id == project_id)
        )
        entities = list(result.scalars().all())
        context["entities"] = [
            {
                "id": str(e.id),
                "type": e.type,
                "name": e.name,
                "description": e.description,
                "attributes": e.attributes,
            }
            for e in entities
        ]
        
        # Get all agents with their goals
        result = await db.execute(
            select(Agent).where(Agent.project_id == project_id)
        )
        agents = list(result.scalars().all())
        
        for agent in agents:
            # Get agent's goals
            result_goals = await db.execute(
                select(Goal).where(
                    Goal.agent_id == agent.id,
                    Goal.status == "active"
                )
            )
            agent_goals = list(result_goals.scalars().all())
            
            context["agents"].append({
                "id": str(agent.id),
                "name": agent.name,
                "type": agent.agent_type,
                "role": agent.role,
                "entity_id": str(agent.entity_id) if agent.entity_id else None,
                "personality": agent.personality,
                "goals": [
                    {
                        "description": g.description,
                        "type": g.goal_type,
                        "priority": g.priority,
                        "progress": g.progress,
                    }
                    for g in agent_goals
                ],
            })
        
        # Get all scenarios
        result = await db.execute(
            select(DBScenario).where(DBScenario.project_id == project_id)
        )
        scenarios = list(result.scalars().all())
        context["scenarios"] = [
            {
                "id": str(s.id),
                "title": s.title,
                "description": s.description,
                "category": s.category,
            }
            for s in scenarios
        ]
        
        # Get timeline events from scenarios
        for scenario in scenarios:
            result_events = await db.execute(
                select(DBTimelineEvent).where(
                    DBTimelineEvent.scenario_id == scenario.id
                ).order_by(DBTimelineEvent.year)
            )
            events = list(result_events.scalars().all())
            context["timeline_events"].extend([
                {
                    "scenario_id": str(scenario.id),
                    "year": e.year,
                    "description": e.description,
                    "impact": e.impact,
                }
                for e in events
            ])
        
        # Get recent world events
        # First get world state
        result_ws = await db.execute(
            select(WorldState).where(WorldState.project_id == project_id)
        )
        world_state_obj = result_ws.scalar_one_or_none()
        
        world_events = []
        if world_state_obj:
            result = await db.execute(
                select(WorldEvent)
                .where(WorldEvent.world_state_id == world_state_obj.id)
                .order_by(WorldEvent.occurred_at.desc())
                .limit(time_window * 10)
            )
            world_events = list(result.scalars().all())
        
        context["world_events"] = [
            {
                "type": e.event_type,
                "description": e.description,
                "impact": e.impact_score,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in world_events
        ]
        
        # Get recent agent actions
        result = await db.execute(
            select(AgentAction)
            .where(AgentAction.project_id == project_id)
            .order_by(AgentAction.created_at.desc())
            .limit(time_window * 20)
        )
        actions = list(result.scalars().all())
        context["actions"] = [
            {
                "agent_id": str(a.agent_id),
                "action": a.action_type,
                "reasoning": a.reasoning,
                "success": a.success,
                "outcome": a.outcome,
                "step": a.simulation_step,
            }
            for a in actions
        ]
        
        # Get all relationships
        result = await db.execute(
            select(AgentRelationship).where(AgentRelationship.project_id == project_id)
        )
        relationships = list(result.scalars().all())
        context["relationships"] = [
            {
                "agent_a_id": str(r.agent_a_id),
                "agent_b_id": str(r.agent_b_id),
                "type": r.relationship_type,
                "strength": r.strength,
                "trust": r.trust,
                "interaction_count": r.interaction_count,
            }
            for r in relationships
        ]
        
        # Get recent interactions
        for rel in relationships:
            result_interactions = await db.execute(
                select(AgentInteraction)
                .where(AgentInteraction.relationship_id == rel.id)
                .order_by(AgentInteraction.occurred_at.desc())
                .limit(5)
            )
            interactions = list(result_interactions.scalars().all())
            context["interactions"].extend([
                {
                    "agent_a_id": str(rel.agent_a_id),
                    "agent_b_id": str(rel.agent_b_id),
                    "type": i.interaction_type,
                    "description": i.description,
                    "outcome": i.outcome,
                    "trust_change": i.trust_change,
                    "strength_change": i.strength_change,
                }
                for i in interactions
            ])
        
        logger.debug(
            f"Context gathered: {len(context['entities'])} entities, "
            f"{len(context['agents'])} agents, {len(context['scenarios'])} scenarios, "
            f"{len(context['actions'])} actions, {len(context['relationships'])} relationships"
        )
        
        return context
    
    def _build_pattern_prompt(self, context: Dict[str, Any]) -> str:
        """Build comprehensive pattern detection prompt"""
        
        # Format entities
        entities_text = "\n".join([
            f"- {e['name']} ({e['type']}): {e['description']}"
            for e in context["entities"][:20]  # Limit to avoid token overflow
        ])
        
        # Format agents with goals
        agents_text = "\n".join([
            f"- {a['name']} ({a['type']}, {a['role']})\n"
            f"  Goals: {', '.join([g['description'] for g in a['goals'][:3]])}"
            for a in context["agents"][:15]
        ])
        
        # Format scenarios
        scenarios_text = "\n".join([
            f"- {s['title']}: {s['description'][:100]}..."
            for s in context["scenarios"][:10]
        ])
        
        # Format timeline events
        timeline_text = "\n".join([
            f"- Year {e['year']}: {e['description']} (impact: {e['impact']})"
            for e in context["timeline_events"][:20]
        ])
        
        # Format recent actions
        actions_text = "\n".join([
            f"- Step {a['step']}: Agent {a['agent_id'][:8]} {a['action']} "
            f"({'SUCCESS' if a['success'] else 'FAILED'}): {a['outcome'][:80]}..."
            for a in context["actions"][:30]
        ])
        
        # Format relationships
        relationships_text = "\n".join([
            f"- Agent {r['agent_a_id'][:8]} ↔ Agent {r['agent_b_id'][:8]}: "
            f"{r['type']} (strength: {r['strength']:.1f}, trust: {r['trust']:.1f}, "
            f"interactions: {r['interaction_count']})"
            for r in context["relationships"][:20]
        ])
        
        # Format interactions
        interactions_text = "\n".join([
            f"- {i['type']}: {i['description']} ({i['outcome']}, "
            f"trust Δ{i['trust_change']:+.1f}, strength Δ{i['strength_change']:+.1f})"
            for i in context["interactions"][:20]
        ])
        
        prompt = f"""You are analyzing a complex simulation with autonomous agents, entities, and evolving scenarios.

ENTITIES IN THE WORLD:
{entities_text if entities_text else "No entities yet"}

AGENTS (Autonomous Decision-Makers):
{agents_text if agents_text else "No agents yet"}

SCENARIOS (Possible Futures):
{scenarios_text if scenarios_text else "No scenarios yet"}

TIMELINE EVENTS:
{timeline_text if timeline_text else "No timeline events yet"}

RECENT AGENT ACTIONS:
{actions_text if actions_text else "No actions yet"}

AGENT RELATIONSHIPS:
{relationships_text if relationships_text else "No relationships yet"}

RECENT INTERACTIONS:
{interactions_text if interactions_text else "No interactions yet"}

TASK: Analyze this simulation data and identify EMERGENT PATTERNS.

Look for patterns that weren't explicitly programmed, such as:
1. **Alliance Formation**: Agents cooperating, forming coalitions
2. **Conflict Escalation**: Tensions rising, arms races, hostilities
3. **Economic Trends**: Wealth concentration, market dominance, trade networks
4. **Social Movements**: Ideology spreading, cultural shifts
5. **Power Shifts**: Influence changing, hierarchies forming
6. **Arms Races**: Competitive buildup of capabilities
7. **Trade Networks**: Economic interdependencies forming
8. **Revolutions**: Challenges to established order

For each pattern you identify:
- Provide a clear title and description
- Rate its significance (0.0 to 1.0)
- List involved agents and entities
- Provide specific evidence from the data

Also provide:
- Overall trends you observe
- Predictions for future developments

Focus on EMERGENT behavior - things that arose from agent interactions, not things that were directly programmed.
"""
        
        return prompt
    
    async def _save_pattern(
        self,
        db: AsyncSession,
        project_id: UUID,
        detected: DetectedPattern,
        context: Dict[str, Any],
    ) -> EmergentPattern:
        """Save detected pattern to database"""
        
        # Map agent names to IDs
        agent_ids = []
        for agent_name in detected.involved_agents:
            for agent in context["agents"]:
                if agent["name"].lower() in agent_name.lower():
                    agent_ids.append(agent["id"])
                    break
        
        # Map entity names to IDs
        entity_ids = []
        for entity_name in detected.involved_entities:
            for entity in context["entities"]:
                if entity["name"].lower() in entity_name.lower():
                    entity_ids.append(entity["id"])
                    break
        
        # Get current simulation step
        result = await db.execute(
            select(AgentAction)
            .where(AgentAction.project_id == project_id)
            .order_by(AgentAction.simulation_step.desc())
            .limit(1)
        )
        last_action = result.scalar_one_or_none()
        current_step = last_action.simulation_step if last_action else 0
        
        # Create pattern
        pattern = EmergentPattern(
            id=uuid4(),
            project_id=project_id,
            pattern_type=detected.pattern_type,
            title=detected.title,
            description=detected.description,
            significance=detected.significance,
            involved_agent_ids=agent_ids,
            involved_entity_ids=entity_ids,
            evidence=detected.evidence,
            first_detected_step=current_step,
            last_updated_step=current_step,
            detected_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        db.add(pattern)
        await db.commit()
        await db.refresh(pattern)
        
        logger.info(f"Pattern saved: {pattern.title} (significance: {pattern.significance:.2f})")
        return pattern
