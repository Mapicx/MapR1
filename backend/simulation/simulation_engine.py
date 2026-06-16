"""
Simulation Engine

Runs automatic simulation with LLM-powered agent decisions.
Coordinates decision-making, action execution, and pattern detection.
"""

import asyncio
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models.action_models import SimulationState, SimulationStepResult, ActionResponse
from backend.models.action_models import AgentAction
from backend.models.agent_models import Agent
from backend.models.world_models import WorldState, StructuredWorldState
from backend.repositories.agent_repository import AgentRepository
from backend.agents.decision_engine import DecisionEngine
from backend.models.action_models import AgentAction
"""
Simulation Engine

Runs automatic simulation with LLM-powered agent decisions.
Coordinates decision-making, action execution, and pattern detection.
"""

import asyncio
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models.action_models import SimulationState, SimulationStepResult, ActionResponse, AgentAction, DiaryEntry
from backend.models.agent_models import Agent
from backend.models.world_models import WorldState, StructuredWorldState
from backend.repositories.agent_repository import AgentRepository
from backend.agents.decision_engine import DecisionEngine
from backend.models.action_models import AgentAction
from backend.agents.agent_memory import AgentMemoryManager
from backend.simulation.action_executor_v2 import ActionExecutorV2
from backend.simulation.consequence_engine import ConsequenceEngine
from backend.systems.delayed_effect_system import DelayedEffectSystem
from backend.agents.action_cooldown import ActionCooldownManager
from backend.simulation.pattern_detector import PatternDetector
from backend.core.sim_logger import get_sim_logger, close_sim_logger
from backend.systems.economy_system import EconomySystem
from backend.systems.scarcity_system import ScarcityEngine
from backend.systems.trust_system import TrustMisinformationSystem
from backend.systems.fog_system import FogOfWarSystem
from backend.systems.psychology_system import PsychologySystem
from backend.systems.black_swan_system import BlackSwanSystem
from backend.theater.tension_tracker import tension_tracker
from backend.systems.tension_modifier_system import TensionModifierSystem
from backend.theater.theater_models import TensionMetrics
import random

class SimulationEngine:
    """Runs automatic simulation with autonomous agents"""
    
    def __init__(self):
        self.decision_engine = DecisionEngine()
        self.action_executor = ActionExecutorV2()
        self.consequence_engine = ConsequenceEngine()
        self.pattern_detector = PatternDetector()
        self.delayed_system = DelayedEffectSystem()
        self.economy_system = EconomySystem()
        self.scarcity_engine = ScarcityEngine()
        self.trust_system = TrustMisinformationSystem()
        self.fog_system = FogOfWarSystem()
        self.psychology_system = PsychologySystem()
        self.black_swan_system = BlackSwanSystem()
        self.running_simulations: Dict[UUID, bool] = {}
        self.diary_logs: Dict[UUID, Dict[str, List[DiaryEntry]]] = {}
    
    async def simulate_step(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> SimulationStepResult:
        """
        Run one simulation step.
        
        Process:
        1. Get all active agents
        2. Each agent perceives world
        3. Each agent makes decision (LLM)
        4. Execute actions (full execution)
        5. Update world state
        6. Detect emergent patterns (LLM)
        
        Args:
            project_id: Project to simulate
        
        Returns:
            SimulationStepResult with actions and patterns
        """
        logger.info(f"Running simulation step for project {project_id}")

        # Get or create simulation state
        sim_state = await self._get_or_create_sim_state(db, project_id)
        current_step = sim_state.current_step + 1

        if project_id not in self.diary_logs:
            self.diary_logs[project_id] = {}

        # Get all agents
        agent_repo = AgentRepository(db)
        agents = await agent_repo.list_agents(project_id=project_id)

        if not agents:
            logger.warning(f"No agents found for project {project_id}")
            return SimulationStepResult(
                step_number=current_step,
                actions=[],
                events_generated=0,
                patterns_detected=0,
                timestamp=datetime.utcnow(),
            )

        logger.info(f"Step {current_step}: {len(agents)} agents will act")

        # Get current world state
        world_state = await self._get_world_state(db, project_id)
        
        # Initialize ThemeResolver
        theme_resolver = None
        if world_state and world_state.state:
            metadata = world_state.state.get("metadata", {})
            theme_data = metadata.get("theme")
            if theme_data:
                from backend.models.compiled_model import CompiledTheme
                from backend.seeder.theme_resolver import ThemeResolver
                try:
                    compiled_theme = CompiledTheme(**theme_data)
                    theme_resolver = ThemeResolver(compiled_theme)
                except Exception as e:
                    logger.error(f"Failed to load CompiledTheme from metadata: {e}")
        
        # 1. FIRE DELAYED EVENTS BEFORE AGENT DECISIONS
        if world_state:
            await self.delayed_system.check_and_fire(db, current_step, project_id, world_state)
            
            # 2. ROLL BLACK SWANS
            self.black_swan_system.roll(world_state, current_step, project_id, db)
            
        # Save old state for cooldown resets
        old_world_state_dict = world_state.state.copy() if world_state and world_state.state else {}

        # Structured logger for this project
        sim_log = get_sim_logger(project_id)
        sim_log.log_step_start(current_step, len(agents))

        # Log world state snapshot
        if world_state and world_state.state:
            sim_log.log_world_state(current_step, world_state.state)

        collapsed_candidates = []
        
        # Each agent acts
        actions = []
        for agent_ref in agents:
            try:
                # Reload the agent to prevent MissingGreenlet errors if a previous iteration called db.rollback()
                agent = await db.get(Agent, agent_ref.id)
                if not agent:
                    continue
                    
                if agent.status == "collapsed":
                    logger.debug(f"Skipping collapsed agent {agent.name}")
                    continue

                # Get current allies with trust scores
                from backend.agents.relationship_system import RelationshipManager
                rel_manager = RelationshipManager(agent.id)
                relationships = await rel_manager.get_all_relationships(db)
                
                structured = self.action_executor._get_structured_state(world_state)
                my_alliances = [a for a in structured.alliances if str(agent.id) in (a.agent_a, a.agent_b)]
                
                current_allies = []
                for alliance in my_alliances:
                    partner_id_str = alliance.agent_b if alliance.agent_a == str(agent.id) else alliance.agent_a
                    partner = await db.get(Agent, UUID(partner_id_str))
                    if partner:
                        trust_score = 0.5
                        if relationships:
                            rel = next((r for r in relationships if str(r.agent_b_id) == partner_id_str), None)
                            if rel:
                                trust_score = rel.trust
                        current_allies.append((partner.name, trust_score))

                # Build situation description
                situation = await self._describe_situation(
                    db, project_id, world_state, agent, theme_resolver, current_allies
                )

                # Get available actions for this agent type
                available_actions = self.decision_engine.get_available_actions_for_agent(agent)

                # Agent decides (LLM)
                logger.debug(f"Agent {agent.name} making decision...")
                decision = await self.decision_engine.make_decision(
                    db,
                    agent=agent,
                    situation=situation,
                    available_actions=available_actions,
                    current_step=current_step,
                    world_state=world_state,
                    theme_resolver=theme_resolver,
                    current_allies=current_allies,
                )

                # Log the LLM decision
                sim_log.log_decision(
                    step=current_step,
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    agent_type=agent.agent_type,
                    agent_role=agent.role,
                    action=decision.action,
                    reasoning=decision.reasoning,
                    confidence=decision.confidence,
                    expected_outcome=decision.expected_outcome,
                    risks=decision.risks,
                    affected_agents=decision.affected_agents,
                )

# -- RESOLVE PENDING PROPOSALS IN PARALLEL --
                if decision.proposal_responses:
                    from backend.agents.relationship_system import RelationshipManager
                    from backend.models.world_models import AllianceRecord, WorldEventRecord
                    
                    structured = self.action_executor._get_structured_state(world_state)
                    proposals_to_remove = []
                    
                    for prop_id, response in decision.proposal_responses.items():
                        proposal = next((p for p in structured.pending_proposals if p.get("id") == prop_id), None)
                        if proposal:
                            target_id_str = proposal.get("from_agent_id")
                            target_name = proposal.get("from_agent_name")
                            prop_type = proposal.get("type")
                            logger.info(f"🤝 {agent.name} {response.upper()}ED the {prop_type} proposal from {target_name}!")
                            
                            if response.lower() == "accept":
                                # Coalitions are not a separate mechanic. 
                                # All multi-party relationships are modeled as bilateral alliances. 
                                # Coalition support is future work.
                                if prop_type == "alliance":
                                    structured.alliances.append(AllianceRecord(
                                        agent_a=str(agent.id),
                                        agent_b=target_id_str,
                                        formed_at_step=current_step,
                                        strength=0.5,
                                        alliance_type="strategic"
                                    ))
                                    structured.agent_power[str(agent.id)] = min(1.0, structured.agent_power.get(str(agent.id), 0.5) + 0.15)
                                    structured.agent_power[target_id_str] = min(1.0, structured.agent_power.get(target_id_str, 0.5) + 0.15)
                                    structured.recent_events.append(WorldEventRecord(
                                        step=current_step, actor=agent.name, action="alliance_formed", target=target_name,
                                        outcome=f"{agent.name} formed an alliance with {target_name}", visibility=1.0
                                    ))
                                    rel_manager = RelationshipManager(agent.id)
                                    await rel_manager.record_interaction(db, project_id, UUID(target_id_str), "cooperation", "Formed an alliance", "positive", 0.5, 0.8)
                                elif prop_type == "relationship":
                                    rel_manager = RelationshipManager(agent.id)
                                    await rel_manager.record_interaction(db, project_id, UUID(target_id_str), "cooperation", "Accepted relationship proposal", "positive", 0.3, 0.5)
                            else:
                                rel_manager = RelationshipManager(agent.id)
                                await rel_manager.record_interaction(db, project_id, UUID(target_id_str), "conflict", "Rejected proposal", "negative", -0.2, -0.1)
                                
                            proposals_to_remove.append(proposal)
                    
                    for p in proposals_to_remove:
                        if p in structured.pending_proposals:
                            structured.pending_proposals.remove(p)
                            
                    # Cleanup stale
                    structured.pending_proposals = [p for p in structured.pending_proposals if p.get("step_created", 0) >= current_step - 2]
                    self.action_executor._save_structured_state(world_state, structured)
                    await db.commit()

                # Process outgoing proposals asynchronously
                if getattr(decision, "outgoing_proposals", None):
                    structured = self.action_executor._get_structured_state(world_state)
                    for outgoing in decision.outgoing_proposals:
                        target_name = outgoing.get("target_name")
                        if not target_name:
                            continue
                        
                        # BUG 1 Fix: Skip if already an ally
                        if current_allies and any(target_name.lower() == a[0].lower() for a in current_allies):
                            logger.info(f"🚫 {agent.name} tried to propose alliance to {target_name}, but they are already allies. Skipped.")
                            continue
                            
                        prop_type = outgoing.get("type", "relationship")
                        context = outgoing.get("context", "Let's form an alliance.")
                        
                        # Find target agent
                        result = await db.execute(select(Agent).where(Agent.project_id == project_id, Agent.name.ilike(f"%{target_name}%")))
                        target_agent = result.scalars().first()
                        
                        if target_agent:
                            structured.pending_proposals.append({
                                "id": str(uuid4()),
                                "from_agent_id": str(agent.id),
                                "from_agent_name": agent.name,
                                "to_agent_id": str(target_agent.id),
                                "to_agent_name": target_agent.name,
                                "type": prop_type,
                                "context": context,
                                "step_created": current_step
                            })
                            logger.info(f"🤝 {agent.name} PROPOSED {prop_type} to {target_agent.name}!")
                    
                    self.action_executor._save_structured_state(world_state, structured)
                    await db.commit()

                # Process intel sharing synchronously
                if getattr(decision, "intel_shares", None):
                    from backend.systems.fog_system import FogOfWarSystem
                    from backend.systems.trust_system import TrustMisinformationSystem
                    
                    fog_system = FogOfWarSystem()
                    trust_system = TrustMisinformationSystem()
                    structured = self.action_executor._get_structured_state(world_state)
                    
                    for intel_share in decision.intel_shares:
                        target_id_str = intel_share.target_agent_id
                        
                        # Verify they are allies
                        agent_id_str = str(agent.id)
                        is_ally = False
                        for alliance in structured.alliances:
                            if agent_id_str in (alliance.agent_a, alliance.agent_b) and target_id_str in (alliance.agent_a, alliance.agent_b):
                                is_ally = True
                                break
                                
                        if not is_ally:
                            logger.info(f"🚫 {agent.name} attempted to share intel with {target_id_str} but they are not allies. Ignored.")
                            continue
                            
                        # Fetch sender's belief state for credibility and propaganda
                        source_state = await trust_system._get_or_create_agent_state(db, agent.id)
                        propaganda = source_state.propaganda_power
                        credibility = source_state.credibility
                        
                        # Flat 0.6 base confidence
                        base_conf = 0.6
                        
                        # Apply distortion intent via propaganda power
                        intent = intel_share.distortion_intent
                        is_fab = intel_share.is_fabricated
                        content = intel_share.fact_content
                        
                        target_agent = next((a for a in agents if str(a.id) == target_id_str), None)
                        target_name = target_agent.name if target_agent else target_id_str
                        logger.info(f"🔍 {agent.name} decided to share intel with {target_name}. Fabricated: {is_fab}. Content: '{content}'. Intent: {intent}.")
                        
                        if intent == "inflate":
                            base_conf += (propaganda * 0.3)
                        elif intent == "deflate":
                            base_conf -= (propaganda * 0.3)
                        elif intent == "mislead":
                            base_conf += (propaganda * 0.2)
                            
                        # Credibility flip formula: (0.4 - credibility) * 0.5
                        if not is_fab and credibility < 0.4:
                            flip_prob = (0.4 - credibility) * 0.5
                            if random.random() < flip_prob:
                                is_fab = True
                                content = f"[Distorted] {content}"
                                logger.info(f"🎲 {agent.name}'s low credibility ({credibility:.2f}) caused unintentional misinformation flip!")
                        
                        final_conf = max(0.1, min(1.0, base_conf))
                        
                        # Target agent
                        target_agent_uuid = UUID(target_id_str)
                        target_res = await db.execute(select(Agent).where(Agent.id == target_agent_uuid))
                        target_agent = target_res.scalars().first()
                        
                        if target_agent:
                            # _reveal_fact adds the fact to the receiver's belief state
                            await fog_system._reveal_fact(
                                db, project_id, target_agent, content, agent.name, final_conf, current_step
                            )
                            logger.info(f"📡 {agent.name} shared intel to {target_agent.name} (Fab: {is_fab}, Conf: {final_conf:.2f})")
                            
                    await db.commit()

                # Evaluate Scarcity
                is_blocked, success_penalty, scarcity_reason = await self.scarcity_engine.evaluate_action(
                    db, project_id, decision.action
                )

                if is_blocked:
                    logger.warning(f"🚫 {agent.name}: {decision.action} BLOCKED by scarcity: {scarcity_reason}")
                    
                    # Log failure without running action
                    from backend.models.action_models import ActionExecutionResult
                    exec_result = ActionExecutionResult(
                        success=False,
                        outcome=scarcity_reason,
                        impact={},
                        side_effects=["Action aborted due to global resource shortage"]
                    )
                else:
                    # Calculate success probability
                    success_prob = 0.6 + (decision.confidence - 0.5) * 0.2
                    if agent.personality.get("rationality", 0.5) > 0.7:
                        success_prob += 0.1
                    if agent.personality.get("ambition", 0.5) > 0.7:
                        success_prob += 0.05
                    if agent.personality.get("risk_tolerance", 0.5) > 0.7:
                        success_prob -= 0.05
                    
                    # Apply scarcity penalty
                    if success_penalty > 0.0:
                        logger.warning(f"⚠️ {agent.name}: {decision.action} penalized by {success_penalty:.2f} due to scarcity: {scarcity_reason}")
                        success_prob -= success_penalty

                    # --- MECHANICAL TENSION: Action Volatility ---
                    structured = self.action_executor._get_structured_state(world_state)
                    tension = getattr(structured, 'tension', 0.0)
                    modifiers = TensionModifierSystem.get_modifiers(tension)
                    
                    # Volatility pushes success probability toward 0.5 (pure chaos)
                    if modifiers.action_volatility > 1.0:
                        diff = success_prob - 0.5
                        success_prob = 0.5 + (diff / modifiers.action_volatility)

                    success_prob = max(0.1, min(0.95, success_prob))
                    
                    # Double success probability for exploitative actions against collapsed agents
                    if decision.action.lower() in ["acquire_company", "exploit_vulnerability", "poach_talent"]:
                        target_name = decision.affected_agents[0] if decision.affected_agents else None
                        if target_name:
                            target_agent = next((a for a in agents if a.name.lower() == target_name.lower()), None)
                            if target_agent and target_agent.status == "collapsed":
                                success_prob = min(1.0, success_prob * 2)
                                logger.info(f"Target {target_name} is collapsed. Double success prob applied.")
                    
                    success = random.random() < success_prob

                    # Pre-execution Sabotage Guard (BUG 4)
                    if decision.action.lower() in ["attack", "sabotage"] and current_allies:
                        target_name = decision.affected_agents[0] if decision.affected_agents else None
                        if target_name and any(target_name.lower() == a[0].lower() for a in current_allies):
                            logger.warning(f"🚨 BETRAYAL DETECTED: {agent.name} is about to attack their ally {target_name}!")
                            from backend.agents.relationship_system import RelationshipManager
                            from backend.models.world_models import WorldEventRecord
                            target_agent = next((a for a in agents if a.name.lower() == target_name.lower()), None)
                            if target_agent:
                                # 1 & 2: Dissolve alliance, set trust to 0, declare rivalry
                                rel_manager = RelationshipManager(agent.id)
                                await rel_manager.create_or_update_relationship(db, project_id, target_agent.id, "rival", strength=-0.8, trust=0.0)
                                
                                target_rel_mgr = RelationshipManager(target_agent.id)
                                await target_rel_mgr.create_or_update_relationship(db, project_id, agent.id, "rival", strength=-0.8, trust=0.0)

                                # Remove alliance from structured state
                                structured = self.action_executor._get_structured_state(world_state)
                                structured.alliances = [a for a in structured.alliances if not (
                                    (a.agent_a == str(agent.id) and a.agent_b == str(target_agent.id)) or
                                    (a.agent_b == str(agent.id) and a.agent_a == str(target_agent.id))
                                )]
                                
                                from backend.models.world_models import RivalryRecord
                                structured.rivalries.append(RivalryRecord(
                                    agent_a=str(agent.id),
                                    agent_b=str(target_agent.id),
                                    intensity=0.8,
                                    cause="Betrayal",
                                    discovered_at_step=current_step
                                ))

                                # Log betrayal event
                                structured.recent_events.append(WorldEventRecord(
                                    step=current_step, actor=agent.name, action="betrayal", target=target_agent.name,
                                    outcome=f"{agent.name} betrayed {target_agent.name}, shattering their alliance!", visibility=1.0
                                ))
                                self.action_executor._save_structured_state(world_state, structured)
                                await db.commit()

                    # Execute action (full execution)
                    logger.debug(f"Executing action: {decision.action}")
                    exec_result = await self.action_executor.execute_action(
                        db,
                        agent=agent,
                        decision=decision,
                        world_state=world_state,
                        simulation_step=current_step,
                        success=success,
                    )
                    
                    # Fog of War: Broadcast the action outcome
                    # Default base visibility to 0.5 unless overridden
                    structured = self.action_executor._get_structured_state(world_state)
                    actor_exposure = structured.agent_exposure.get(str(agent.id), 0.5)
                    target_name = decision.affected_agents[0] if decision.affected_agents else None
                    await self.fog_system.broadcast_event(
                        db, project_id, agent.name, target_name, exec_result.outcome,
                        base_visibility=0.5, actor_exposure=actor_exposure, all_agents=agents, current_step=current_step
                    )
                    
                    # -------------------------------------------------------------
                    # Collapse Check (evaluated BEFORE psychology updates per specs)
                    # -------------------------------------------------------------
                    if current_step >= 3:
                        res = structured.agent_resources.get(str(agent.id), 0.5)
                        psych = agent.mutable_psychology or {}
                        failures = psych.get("consecutive_failures", 0)
                        desperation = psych.get("desperation", 0.0)
                        
                        if res <= 0.08 and failures >= 4 and desperation >= 0.8:
                            collapsed_candidates.append(agent)
                    
                    # Update Agent Psychology based on action outcome
                    await self.psychology_system.update_agent_psychology(
                        db, agent, decision.action, exec_result, structured
                    )

                # Track Diary Entry
                action_taken_label = decision.action
                if theme_resolver and hasattr(theme_resolver, "theme") and hasattr(theme_resolver.theme, "vocabulary_map"):
                    action_taken_label = theme_resolver.theme.vocabulary_map.get(decision.action, decision.action)
                
                agent_psych = agent.mutable_psychology or {}
                diary_entry = DiaryEntry(
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    step_number=current_step,
                    action_taken=action_taken_label,
                    action_succeeded=exec_result.success if 'exec_result' in locals() else False,
                    reasoning=decision.reasoning if decision.reasoning else "No reasoning recorded.",
                    psychology_snapshot={
                        "fear": agent_psych.get("fear", 0.0),
                        "paranoia": agent_psych.get("paranoia", 0.0),
                        "desperation": agent_psych.get("desperation", 0.0),
                        "greed": agent_psych.get("greed", 0.0),
                        "radicalization": agent_psych.get("radicalization", 0.0)
                    },
                    allies_at_time=[a[0] for a in current_allies] if current_allies else []
                )
                if str(agent.id) not in self.diary_logs[project_id]:
                    self.diary_logs[project_id][str(agent.id)] = []
                self.diary_logs[project_id][str(agent.id)].append(diary_entry)

                # Create action record
                action_record = AgentAction(
                    id=uuid4(),
                    agent_id=agent.id,
                    project_id=project_id,
                    simulation_step=current_step,
                    action_type=decision.action,
                    description=decision.action,
                    reasoning=decision.reasoning,
                    confidence=decision.confidence,
                    executed=True,
                    success=exec_result.success,
                    outcome=exec_result.outcome,
                    impact=exec_result.impact,
                    created_at=datetime.utcnow(),
                    executed_at=datetime.utcnow(),
                )
                db.add(action_record)

                # Store as memory
                memory_manager = AgentMemoryManager(agent.id)
                await memory_manager.remember(
                    db,
                    memory_type="observation",
                    content=exec_result.outcome,
                    importance=0.7 if exec_result.success else 0.5,
                    emotional_valence=0.5 if exec_result.success else -0.3,
                )
                await db.commit()

                # Log the execution result
                sim_log.log_action(
                    step=current_step,
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    action_type=decision.action,
                    success=exec_result.success,
                    outcome=exec_result.outcome,
                    impact=exec_result.impact,
                    side_effects=exec_result.side_effects,
                )

                # Convert to response (BUG 2 Fix: copy affected_agents to impact for consequence_engine)
                # action_executor_v2 returns affected_agents as a list of UUIDs. consequence_engine expects string UUIDs in impact.
                final_impact = exec_result.impact.copy()
                if exec_result.affected_agents:
                    final_impact["affected_agents"] = [str(uid) for uid in exec_result.affected_agents]
                    
                action_response = ActionResponse(
                    id=action_record.id,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    action_type=decision.action,
                    description=decision.action,
                    reasoning=decision.reasoning,
                    confidence=decision.confidence,
                    executed=True,
                    success=exec_result.success,
                    outcome=exec_result.outcome,
                    impact=final_impact,
                    public_impact=exec_result.public_impact,
                    simulation_step=current_step,
                    created_at=action_record.created_at,
                )

                actions.append(action_response)

                logger.info(
                    f"✓ {agent.name}: {decision.action} "
                    f"({'SUCCESS' if exec_result.success else 'FAILED'})"
                )

            except Exception as e:
                # Use __dict__ to avoid lazy loading MissingGreenlet errors if session state is altered
                agent_name = agent.__dict__.get('name', str(getattr(agent_ref, 'id', 'Unknown'))) if 'agent' in locals() else str(getattr(agent_ref, 'id', 'Unknown'))
                logger.error(f"Error processing agent {agent_name}: {e}")
                sim_log.log_error(f"agent:{agent_name}", str(e))
                # Roll back any partial transaction so the next agent starts clean
                await db.rollback()
                continue

        # Propagate consequences after all agents have acted
        logger.info("Propagating consequences...")
        new_events = await self.consequence_engine.propagate(
            db=db,
            world_state=world_state,
            actions_this_step=actions,
            current_step=current_step,
        )

        # Update persistent world economy
        logger.info("Updating world economy...")
        
        world_state_changes = {}
        
        # Get actual action models to pass to economy system
        action_records = []
        for a in actions:
            # Reconstruct dummy AgentAction for the economy system if needed
            # The economy system only needs action_type and executed flag
            dummy_action = AgentAction(action_type=a.action_type, executed=a.executed)
            action_records.append(dummy_action)
            
        economy_result = await self.economy_system.update(
            db=db, 
            project_id=project_id, 
            actions=action_records, 
            structured_world=self.action_executor._get_structured_state(world_state)
        )
        
        # Track price changes or shortages
        if economy_result.get("price_changes"):
            world_state_changes["price_changes"] = economy_result["price_changes"]

        # Check world state changes for cooldown logic
        if world_state and world_state.state:
            cooldown_mgr = ActionCooldownManager()
            cooldown_mgr.check_world_state_change(old_world_state_dict, world_state.state)

        # Detect emergent patterns (LLM with full context)
        logger.info("Detecting emergent patterns...")
        patterns = await self.pattern_detector.detect_patterns(
            db,
            project_id=project_id,
            time_window=10,
            min_significance=0.5,
        )

        # Log each detected pattern
        for pattern in patterns:
            sim_log.log_pattern(
                step=current_step,
                pattern_id=str(pattern.id),
                pattern_type=pattern.pattern_type,
                title=pattern.title,
                description=pattern.description,
                significance=pattern.significance,
                involved_agents=[str(a) for a in (pattern.involved_agent_ids or [])],
                evidence=pattern.evidence or [],
                predictions=[],
            )

        sim_log.log_step_end(current_step, len(actions), len(patterns))

        # --- Compute and persist mechanical tension ---
        logger.info("Computing mechanical tension...")
        structured = self.action_executor._get_structured_state(world_state)
        history_dicts = structured.metadata.get("tension_history", [])
        
        history = []
        for h in history_dicts:
            try:
                history.append(TensionMetrics(**h))
            except Exception:
                pass

        metrics = tension_tracker.compute_tension(
            step=current_step,
            actions=actions,
            world_state=structured,
            history=history
        )
        
        history.append(metrics)
        structured.metadata["tension_history"] = [m.model_dump() for m in history[-10:]]
        structured.tension = metrics.overall_tension
        
        # --- Apply tension-based trust decay ---
        from backend.systems.tension_modifier_system import apply_tension_to_trust_decay
        from backend.agents.relationship_system import RelationshipManager
        for alliance in structured.alliances:
            try:
                agent_a_id = UUID(alliance.agent_a)
                agent_b_id = UUID(alliance.agent_b)
                
                rel_mgr_a = RelationshipManager(agent_a_id)
                rel_a = await rel_mgr_a.get_relationship(db, agent_b_id)
                if rel_a:
                    old_trust = rel_a.trust
                    new_trust = apply_tension_to_trust_decay(old_trust, structured.tension)
                    if new_trust < old_trust:
                        rel_a.trust = new_trust
                        db.add(rel_a)
                        
                rel_mgr_b = RelationshipManager(agent_b_id)
                rel_b = await rel_mgr_b.get_relationship(db, agent_a_id)
                if rel_b:
                    old_trust = rel_b.trust
                    new_trust = apply_tension_to_trust_decay(old_trust, structured.tension)
                    if new_trust < old_trust:
                        rel_b.trust = new_trust
                        db.add(rel_b)
            except Exception as e:
                logger.error(f"Error applying tension trust decay: {e}")
        
        self.action_executor._save_structured_state(world_state, structured)

        # Update simulation state
        sim_state.current_step = current_step
        sim_state.total_actions += len(actions)
        sim_state.last_step_at = datetime.utcnow()
        await db.commit()

        logger.success(
            f"Step {current_step} complete: {len(actions)} actions, "
            f"{len(patterns)} patterns detected"
        )

        return SimulationStepResult(
            step_number=current_step,
            actions=actions,
            events_generated=len(actions),
            patterns_detected=len(patterns),
            world_state_changes=world_state_changes if 'world_state_changes' in locals() else {},
            timestamp=datetime.utcnow(),
        )
    
    async def run_auto_simulation(
        self,
        db: AsyncSession,
        project_id: UUID,
        max_steps: int = 100,
        step_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Run simulation automatically for multiple steps.
        
        Args:
            project_id: Project to simulate
            max_steps: Maximum number of steps
            step_delay: Delay between steps in seconds
        
        Returns:
            Summary of simulation run
        """
        logger.info(
            f"Starting auto-simulation for project {project_id}: "
            f"{max_steps} steps, {step_delay}s delay"
        )
        
        # Mark as running
        self.running_simulations[project_id] = True
        
        # Update simulation state
        sim_state = await self._get_or_create_sim_state(db, project_id)
        sim_state.is_running = True
        sim_state.started_at = datetime.utcnow()
        await db.commit()
        
        step_count = 0
        total_actions = 0
        total_patterns = 0
        
        try:
            while self.running_simulations.get(project_id, False) and step_count < max_steps:
                # Run one step
                step_result = await self.simulate_step(db, project_id)
                
                step_count += 1
                total_actions += len(step_result.actions)
                total_patterns += step_result.patterns_detected
                
                logger.info(
                    f"Auto-simulation step {step_count}/{max_steps}: "
                    f"{len(step_result.actions)} actions, "
                    f"{step_result.patterns_detected} patterns"
                )
                
                # Delay between steps
                if step_count < max_steps:
                    await asyncio.sleep(step_delay)
            
            logger.success(
                f"Auto-simulation completed: {step_count} steps, "
                f"{total_actions} actions, {total_patterns} patterns"
            )
            
        except Exception as e:
            logger.error(f"Auto-simulation error: {e}")
            raise
        finally:
            # Mark as stopped
            self.running_simulations[project_id] = False
            sim_state.is_running = False
            await db.commit()
        
        return {
            "project_id": str(project_id),
            "steps_completed": step_count,
            "total_actions": total_actions,
            "total_patterns": total_patterns,
            "status": "completed",
        }
    
    def stop_simulation(self, project_id: UUID):
        """Stop automatic simulation"""
        logger.info(f"Stopping simulation for project {project_id}")
        self.running_simulations[project_id] = False
    
    def is_running(self, project_id: UUID) -> bool:
        """Check if simulation is running"""
        return self.running_simulations.get(project_id, False)
    
    async def get_simulation_status(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """Get current simulation status"""
        sim_state = await self._get_or_create_sim_state(db, project_id)
        
        return {
            "project_id": str(project_id),
            "current_step": sim_state.current_step,
            "is_running": sim_state.is_running,
            "total_actions": sim_state.total_actions,
            "started_at": sim_state.started_at.isoformat() if sim_state.started_at else None,
            "last_step_at": sim_state.last_step_at.isoformat() if sim_state.last_step_at else None,
        }
    
    async def _get_or_create_sim_state(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> SimulationState:
        """Get or create simulation state"""
        result = await db.execute(
            select(SimulationState).where(SimulationState.project_id == project_id)
        )
        sim_state = result.scalar_one_or_none()
        
        if not sim_state:
            sim_state = SimulationState(
                id=uuid4(),
                project_id=project_id,
                current_step=0,
                is_running=False,
                total_actions=0,
            )
            db.add(sim_state)
            await db.commit()
            await db.refresh(sim_state)
        
        return sim_state
    
    async def _get_world_state(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Optional[WorldState]:
        """Get current world state"""
        result = await db.execute(
            select(WorldState).where(WorldState.project_id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def _describe_situation(
        self, 
        db: AsyncSession, 
        project_id: UUID, 
        world_state: WorldState, 
        agent: Agent,
        theme_resolver: Optional[Any] = None,
        current_allies: List[Tuple[str, float]] = None,
    ) -> str:
        """
        Builds a comprehensive string describing the current world state,
        agent's position, known beliefs, alliances, etc.
        """
        structured = self.action_executor._get_structured_state(world_state)
        
        # Instantiate trust system if not present
        if not hasattr(self, 'trust_system'):
            from backend.systems.trust import TrustMisinformationSystem
            self.trust_system = TrustMisinformationSystem()
            
        # 1. Fetch beliefs
        agent_beliefs = await self.trust_system.get_agent_beliefs(db, agent.id)
        public_beliefs = await self.trust_system.get_public_beliefs(db, project_id)
        
        parts = [f"You are {agent.name}, {agent.role}.", ""]
        
        # ── Section 1: Recent Events ──
        # REPLACED BY FOG OF WAR: Agents only see what is in their known_facts.
        # Recent events are no longer omnisciently leaked here.
        
        # ── Section 2: Your Position ──
        agent_id = str(agent.id)
        parts.append("=== YOUR CURRENT POSITION ===")
        parts.append(f"  Resources: {structured.agent_resources.get(agent_id, 0.5):.0%}")
        parts.append(f"  Reputation: {structured.agent_reputation.get(agent_id, 0.5):.0%}")
        parts.append(f"  Influence: {structured.agent_power.get(agent_id, 0.5):.0%}")
        exposure = structured.agent_exposure.get(agent_id, 0.0)
        if exposure > 0.3:
            parts.append(f"  ⚠ Exposure level: {exposure:.0%} — you are under scrutiny")
        parts.append("")
        
        # ── Section 2.5: World Economy ──
        from backend.models.economy_models import GlobalEconomyState
        economy_result = await db.execute(select(GlobalEconomyState).where(GlobalEconomyState.project_id == project_id))
        economy = economy_result.scalar_one_or_none()
        if economy:
            parts.append("=== GLOBAL ECONOMY SCARCITY ===")
            res1 = theme_resolver.resolve_resource('resource_1') if theme_resolver else 'Resource 1'
            res2 = theme_resolver.resolve_resource('resource_2') if theme_resolver else 'Resource 2'
            parts.append(f"  {res1.title()} Supply: {economy.resource_1_supply:,.0f} units")
            parts.append(f"  {res2.title()} Supply: {economy.resource_2_supply:,.0f} units")
            parts.append(f"  Global Unemployment: {economy.public_unemployment:.1%}")
            parts.append(f"  Market Confidence: {economy.market_confidence:.1%}")
            parts.append("")

        # ── Section 3: Active Alliances ──
        if current_allies:
            parts.append("=== YOUR ALLIANCES ===")
            for partner_name, trust in current_allies:
                parts.append(f"  • Allied with {partner_name} (trust: {trust:.1f})")
            parts.append("")
        
        # ── Section 4: Active Rivalries ──
        my_rivalries = [r for r in structured.rivalries if agent_id in (r.agent_a, r.agent_b)]
        if my_rivalries:
            parts.append("=== THREATS & RIVALRIES ===")
            for rivalry in my_rivalries:
                rival_id = rivalry.agent_b if rivalry.agent_a == agent_id else rivalry.agent_a
                parts.append(f"  • Rivalry with {rival_id} (intensity: {rivalry.intensity:.0%}, cause: {rivalry.cause})")
            parts.append("")

        # ── Section 5: Public Opinion / Beliefs ──
        if public_beliefs:
            parts.append("=== PUBLIC BELIEFS ===")
            for topic, conf in public_beliefs.items():
                res_topic = theme_resolver.resolve_text(topic) if theme_resolver else topic
                if conf > 0.7: parts.append(f"- The public strongly believes: {res_topic} (Consensus: {conf*100:.0f}%)")
                elif conf < 0.3: parts.append(f"- The public widely rejects: {res_topic} (Consensus: {conf*100:.0f}%)")
                else: parts.append(f"- The public is divided on: {res_topic} (Consensus: {conf*100:.0f}%)")
                
        if structured.public_opinion:
            for topic, sentiment in structured.public_opinion.items():
                res_topic = theme_resolver.resolve_text(topic) if theme_resolver else topic
                parts.append(f"- Public sentiment on {res_topic}: {sentiment:.2f} (-1 to 1)")
                
        if not public_beliefs and not structured.public_opinion:
            parts.append("No notable public opinion data.")
        parts.append("")
        
        return "\n".join(parts)


# Global simulation engine instance
simulation_engine = SimulationEngine()
