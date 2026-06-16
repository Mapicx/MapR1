"""
MapR1 — Contextual Consequence Engine

Replaces static failure templates with context-driven, weighted outcome branching.

Each failed action produces consequences that depend on:
- Acting agent psychology (paranoia, fear, ego, desperation, etc.)
- Target relationship state (trust, alliance, rivalry)
- Public visibility and exposure
- Current scarcity / resource levels
- Public opinion and media attention
- Recent failures and betrayal history
- Faction alignment (alliances/rivalries)
- World instability indicators

The same action under different contexts produces different outcomes.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.agent_models import Agent, MutablePsychology
from backend.models.action_models import ActionExecutionResult
from backend.models.world_models import (
    StructuredWorldState,
    WorldEventRecord,
    RivalryRecord,
    WorldState,
)
from backend.agents.agent_memory import AgentMemoryManager
from backend.agents.relationship_system import RelationshipManager
from backend.systems.tension_modifier_system import (
    TensionModifierSystem,
    tension_modifier_system,
    apply_tension_to_psychology_delta,
)


# ============================================================================
# Context Model
# ============================================================================


class ConsequenceContext(BaseModel):
    """
    Structured context object gathered BEFORE consequence resolution.
    Captures the full state needed to determine contextual outcomes.
    """

    # ── Acting agent psychology ──
    paranoia: float = Field(default=0.3, ge=0.0, le=1.0)
    fear: float = Field(default=0.2, ge=0.0, le=1.0)
    ego: float = Field(default=0.5, ge=0.0, le=1.0)
    greed: float = Field(default=0.5, ge=0.0, le=1.0)
    desperation: float = Field(default=0.0, ge=0.0, le=1.0)
    radicalization: float = Field(default=0.1, ge=0.0, le=1.0)
    consecutive_failures: int = Field(default=0, ge=0)

    # ── Target relationship state ──
    target_trust: float = Field(default=0.5, ge=0.0, le=1.0)
    relationship_strength: float = Field(default=0.0, ge=-1.0, le=1.0)
    is_ally: bool = False
    is_rival: bool = False

    # ── Public context ──
    actor_visibility: float = Field(default=0.5, ge=0.0, le=1.0,
                                     description="How exposed/visible the acting agent is")
    actor_reputation: float = Field(default=0.5, ge=0.0, le=1.0)
    public_fear: float = Field(default=0.0, ge=0.0, le=1.0,
                                description="Average public opinion negativity — proxy for fear/panic")

    # ── Resource / scarcity ──
    actor_resources: float = Field(default=0.5, ge=0.0, le=1.0)
    target_resources: float = Field(default=0.5, ge=0.0, le=1.0)
    global_scarcity: float = Field(default=0.0, ge=0.0, le=1.0,
                                    description="0 = abundant, 1 = extreme scarcity")

    # ── History ──
    recent_betrayals: int = Field(default=0, ge=0,
                                   description="Number of betrayals in recent memory")
    recent_failures_total: int = Field(default=0, ge=0,
                                        description="Total recent failures across all agents")

    # ── World instability ──
    world_instability: float = Field(default=0.0, ge=0.0, le=1.0,
                                      description="Composite instability indicator")
    active_rivalries: int = Field(default=0, ge=0)
    active_alliances: int = Field(default=0, ge=0)

    # ── Recent action history ──
    actor_recent_actions: List[str] = Field(default_factory=list,
                                             description="Last N action types by the actor")

    # ── Mechanical Tension ──
    tension: float = Field(default=0.0, ge=0.0, le=1.0,
                           description="Current world tension level - drives mechanical effects")


# ============================================================================
# Contextual Outcome Definition
# ============================================================================


@dataclass
class ConsequenceOutcome:
    """A single possible consequence with its context-dependent weight."""
    key: str                                # unique identifier e.g. "exposed_operative"
    description_template: str               # template with {actor} and {target}
    base_weight: float = 1.0                # default weight before context adjustment

    # World-state side effects
    actor_reputation_delta: float = 0.0
    actor_exposure_delta: float = 0.0
    actor_resources_delta: float = 0.0
    actor_power_delta: float = 0.0
    target_trust_delta: float = 0.0         # trust the target has in the actor
    target_resources_delta: float = 0.0
    target_reputation_delta: float = 0.0

    # Psychology mutations on the ACTOR
    actor_paranoia_delta: float = 0.0
    actor_fear_delta: float = 0.0
    actor_desperation_delta: float = 0.0
    actor_ego_delta: float = 0.0
    actor_radicalization_delta: float = 0.0

    # Whether to create a rivalry
    creates_rivalry: bool = False
    rivalry_intensity: float = 0.5

    # Visibility of the consequence event
    event_visibility: float = 0.8

    # Memory to record on target
    target_memory: Optional[str] = None
    target_memory_importance: float = 0.9
    target_memory_valence: float = -0.8

    # Memory to record on actor
    actor_memory: Optional[str] = None
    actor_memory_importance: float = 0.7
    actor_memory_valence: float = -0.5

    # Delayed effect scheduling
    delayed_effect: Optional[Dict[str, Any]] = None


# ============================================================================
# Action Family Outcome Tables
# ============================================================================

SABOTAGE_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="exposed_operative",
        description_template="{actor}'s sabotage operative was caught and exposed by {target}!",
        base_weight=1.0,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.5,
        target_trust_delta=-0.8,
        creates_rivalry=True,
        rivalry_intensity=0.8,
        event_visibility=1.0,
        target_memory="{actor} tried to sabotage us — their operative was caught",
        actor_memory="My sabotage attempt on {target} was exposed — I'm now a known threat",
    ),
    ConsequenceOutcome(
        key="retaliation_escalation",
        description_template="{target} discovered {actor}'s sabotage plot and is escalating retaliation!",
        base_weight=0.8,
        actor_reputation_delta=-0.2,
        actor_exposure_delta=0.3,
        actor_power_delta=-0.15,
        target_trust_delta=-1.0,
        creates_rivalry=True,
        rivalry_intensity=0.9,
        event_visibility=0.9,
        target_memory="{actor} tried to sabotage me — I must retaliate with full force",
        target_memory_importance=0.95,
        target_memory_valence=-0.95,
        actor_paranoia_delta=0.15,
    ),
    ConsequenceOutcome(
        key="accidental_collateral",
        description_template="{actor}'s botched sabotage caused collateral damage to innocent parties near {target}!",
        base_weight=0.6,
        actor_reputation_delta=-0.25,
        actor_resources_delta=-0.1,
        event_visibility=0.85,
        target_memory="{actor}'s sabotage attempt caused collateral damage around us",
        actor_memory="My sabotage against {target} went wrong — collateral damage occurred",
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="internal_leak",
        description_template="An insider leaked {actor}'s sabotage plans to {target} before execution!",
        base_weight=0.7,
        actor_reputation_delta=-0.15,
        actor_exposure_delta=0.4,
        target_trust_delta=-0.5,
        event_visibility=0.7,
        target_memory="Someone leaked {actor}'s sabotage plans to us — we have a mole on our side too",
        actor_memory="My sabotage plans were leaked — there's a traitor in my ranks",
        actor_paranoia_delta=0.25,
    ),
    ConsequenceOutcome(
        key="paranoia_spike",
        description_template="{target} has become deeply paranoid after detecting {actor}'s sabotage attempt!",
        base_weight=0.5,
        actor_exposure_delta=0.2,
        target_trust_delta=-0.6,
        event_visibility=0.5,
        target_memory="{actor} attempted sabotage — I can't trust anyone now",
        target_memory_importance=0.9,
        target_memory_valence=-0.9,
        actor_memory="My sabotage made {target} paranoid — they'll be harder to approach",
    ),
    ConsequenceOutcome(
        key="resource_drain",
        description_template="{actor}'s failed sabotage burned significant resources with nothing to show for it!",
        base_weight=0.9,
        actor_resources_delta=-0.2,
        actor_power_delta=-0.05,
        event_visibility=0.3,
        actor_memory="My sabotage attempt against {target} drained resources for nothing",
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="alliance_distrust",
        description_template="{actor}'s allies are questioning their methods after the botched sabotage of {target}!",
        base_weight=0.5,
        actor_reputation_delta=-0.15,
        event_visibility=0.6,
        target_memory="{actor}'s own allies are uneasy about their sabotage tactics",
        actor_memory="My allies are concerned about my sabotage attempt on {target}",
        actor_fear_delta=0.05,
    ),
]


POLICY_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="public_backlash",
        description_template="{actor}'s policy push triggered a massive public backlash!",
        base_weight=1.0,
        actor_reputation_delta=-0.25,
        actor_power_delta=-0.15,
        event_visibility=0.95,
        actor_memory="My policy push caused a public backlash — my credibility is damaged",
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_deadlock",
        description_template="{actor}'s policy proposal is trapped in regulatory deadlock!",
        base_weight=0.8,
        actor_power_delta=-0.1,
        event_visibility=0.6,
        actor_memory="My policy proposal got stuck in bureaucratic deadlock",
    ),
    ConsequenceOutcome(
        key="credibility_erosion",
        description_template="{actor}'s failed policy push has eroded their political credibility!",
        base_weight=0.9,
        actor_reputation_delta=-0.2,
        actor_power_delta=-0.1,
        event_visibility=0.7,
        actor_memory="My failed policy push has damaged my credibility among peers",
        actor_desperation_delta=0.05,
    ),
    ConsequenceOutcome(
        key="activist_mobilization",
        description_template="Activists mobilized against {actor}'s policy, turning public opinion!",
        base_weight=0.6,
        actor_reputation_delta=-0.15,
        event_visibility=0.85,
        actor_memory="Activists turned the public against my policy proposal",
    ),
    ConsequenceOutcome(
        key="faction_disagreement",
        description_template="{actor}'s own faction disagrees with the policy direction!",
        base_weight=0.5,
        actor_power_delta=-0.12,
        event_visibility=0.5,
        actor_memory="My own faction is divided over my policy push — internal fracture forming",
        actor_paranoia_delta=0.1,
    ),
    ConsequenceOutcome(
        key="media_humiliation",
        description_template="The media is humiliating {actor} over their failed policy push!",
        base_weight=0.7,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.3,
        event_visibility=1.0,
        actor_memory="The media turned my policy failure into a public spectacle",
        actor_fear_delta=0.15,
    ),
]


BETRAYAL_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="blackmail",
        description_template="{target} now holds evidence of {actor}'s betrayal and is using it as leverage!",
        base_weight=0.8,
        actor_power_delta=-0.2,
        target_trust_delta=-1.0,
        event_visibility=0.4,
        creates_rivalry=True,
        rivalry_intensity=0.85,
        target_memory="{actor} tried to betray me — I have evidence and leverage over them now",
        target_memory_importance=0.95,
        target_memory_valence=-0.9,
        actor_memory="{target} caught my betrayal and is blackmailing me",
        actor_memory_importance=0.95,
        actor_memory_valence=-0.9,
        actor_paranoia_delta=0.2,
    ),
    ConsequenceOutcome(
        key="social_isolation",
        description_template="{actor} has been socially isolated after their betrayal of {target} became known!",
        base_weight=0.9,
        actor_reputation_delta=-0.35,
        actor_exposure_delta=0.4,
        target_trust_delta=-1.0,
        creates_rivalry=True,
        rivalry_intensity=0.7,
        event_visibility=0.9,
        target_memory="{actor} betrayed our trust and is now isolated by everyone",
        actor_memory="My betrayal of {target} is public — I'm being shunned by everyone",
        actor_memory_importance=0.9,
        actor_fear_delta=0.15,
        actor_desperation_delta=0.15,
    ),
    ConsequenceOutcome(
        key="secret_exposure",
        description_template="{actor}'s betrayal exposed their own secrets in the process!",
        base_weight=0.7,
        actor_reputation_delta=-0.2,
        actor_exposure_delta=0.5,
        target_trust_delta=-0.9,
        event_visibility=0.8,
        target_memory="{actor}'s failed betrayal revealed their own hidden secrets",
        actor_memory="In trying to betray {target}, my own secrets were exposed",
        actor_paranoia_delta=0.2,
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="faction_fracture",
        description_template="{actor}'s betrayal has fractured their faction's unity!",
        base_weight=0.6,
        actor_power_delta=-0.2,
        actor_reputation_delta=-0.15,
        target_trust_delta=-0.8,
        event_visibility=0.7,
        target_memory="{actor}'s betrayal caused a fracture in their own organization",
        actor_memory="My betrayal attempt against {target} fractured my own faction",
        actor_paranoia_delta=0.15,
    ),
    ConsequenceOutcome(
        key="loyalty_collapse",
        description_template="News of {actor}'s betrayal caused a collapse in loyalty among their supporters!",
        base_weight=0.7,
        actor_power_delta=-0.25,
        actor_reputation_delta=-0.3,
        target_trust_delta=-1.0,
        creates_rivalry=True,
        rivalry_intensity=0.75,
        event_visibility=0.85,
        target_memory="{actor} betrayed us — their own supporters are abandoning them",
        actor_memory="My betrayal of {target} caused my supporters to lose faith in me",
        actor_desperation_delta=0.2,
    ),
    ConsequenceOutcome(
        key="retaliation_planning",
        description_template="{target} is secretly planning retaliation after {actor}'s betrayal!",
        base_weight=0.8,
        target_trust_delta=-1.0,
        creates_rivalry=True,
        rivalry_intensity=0.9,
        event_visibility=0.3,
        target_memory="{actor} betrayed me — I'm planning careful retaliation",
        target_memory_importance=0.95,
        target_memory_valence=-0.95,
        actor_memory="{target} knows about my betrayal — retaliation may be coming",
        actor_paranoia_delta=0.25,
        actor_fear_delta=0.15,
        delayed_effect={
            "event_type": "retaliation_strike",
            "delay_turns": 2,
            "description": "Retaliation for betrayal by {actor}",
            "impact_data": {"agent_resources": {"{actor_id}": -0.15}},
        },
    ),
]


LEAK_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="misinformation_spiral",
        description_template="{actor}'s leaked information mutated into uncontrolled misinformation!",
        base_weight=0.7,
        actor_reputation_delta=-0.1,
        event_visibility=0.9,
        actor_memory="My leak against {target} spiraled into widespread misinformation",
    ),
    ConsequenceOutcome(
        key="source_discovery",
        description_template="{target} traced the leak back to {actor}!",
        base_weight=1.0,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.5,
        target_trust_delta=-0.9,
        creates_rivalry=True,
        rivalry_intensity=0.7,
        event_visibility=0.8,
        target_memory="{actor} was the one who tried to leak my secrets",
        target_memory_importance=0.95,
        actor_memory="{target} traced the leak back to me — I'm exposed",
        actor_paranoia_delta=0.2,
    ),
    ConsequenceOutcome(
        key="conspiracy_amplification",
        description_template="{actor}'s leak was twisted into conspiracy theories about {target}!",
        base_weight=0.5,
        event_visibility=0.85,
        actor_memory="My leak about {target} was amplified into conspiracy theories — unpredictable",
    ),
    ConsequenceOutcome(
        key="censorship_escalation",
        description_template="Authorities cracked down on information after {actor}'s failed leak!",
        base_weight=0.4,
        actor_reputation_delta=-0.1,
        event_visibility=0.7,
        actor_memory="My failed leak triggered a censorship crackdown",
    ),
    ConsequenceOutcome(
        key="public_panic",
        description_template="{actor}'s leak caused public panic before being debunked!",
        base_weight=0.5,
        actor_reputation_delta=-0.2,
        event_visibility=1.0,
        actor_memory="My leak caused public panic — even though it was debunked, trust eroded",
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="credibility_loss",
        description_template="{actor} was exposed as an unreliable source after the failed leak about {target}!",
        base_weight=0.9,
        actor_reputation_delta=-0.25,
        actor_exposure_delta=0.3,
        event_visibility=0.75,
        actor_memory="I've been labeled as an unreliable source after my leak attempt on {target}",
        actor_desperation_delta=0.1,
    ),
]


ATTACK_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="retaliation_escalation",
        description_template="{target} repelled {actor}'s attack and is escalating retaliation with full force!",
        base_weight=1.0,
        actor_power_delta=-0.15,
        actor_exposure_delta=0.4,
        target_trust_delta=-1.0,
        creates_rivalry=True,
        rivalry_intensity=0.95,
        event_visibility=0.95,
        target_memory="{actor} attacked us and failed — we must crush them before they try again",
        target_memory_importance=0.95,
        target_memory_valence=-0.95,
        actor_memory="My attack on {target} failed and they're retaliating — I'm in danger",
        actor_paranoia_delta=0.15,
        actor_fear_delta=0.1,
        actor_ego_delta=-0.1,
        delayed_effect={"event_type": "retaliation_strike", "delay_turns": 2, "description": "{target} launches a counter-attack against {actor}"},
    ),
    ConsequenceOutcome(
        key="public_condemnation",
        description_template="{actor}'s failed attack on {target} triggered widespread public condemnation!",
        base_weight=0.9,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.5,
        event_visibility=1.0,
        target_memory="{actor}'s attack on us backfired — public opinion has turned against them",
        actor_memory="My attack on {target} was condemned publicly — my reputation is damaged",
        actor_ego_delta=-0.1,
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="alliance_intervention",
        description_template="{target}'s allies intervened to repel {actor}'s attack, forming a coalition!",
        base_weight=0.7,
        actor_power_delta=-0.2,
        actor_exposure_delta=0.3,
        target_trust_delta=-0.7,
        creates_rivalry=True,
        rivalry_intensity=0.8,
        event_visibility=0.85,
        target_memory="{actor} attacked us — our allies came to our defense",
        actor_memory="My attack on {target} was stopped by their allies — I'm now outnumbered",
        actor_fear_delta=0.15,
        actor_paranoia_delta=0.1,
    ),
    ConsequenceOutcome(
        key="civilian_panic",
        description_template="{actor}'s failed attack caused collateral panic among civilians near {target}!",
        base_weight=0.6,
        actor_reputation_delta=-0.35,
        actor_resources_delta=-0.1,
        event_visibility=0.9,
        target_memory="{actor}'s attack caused panic among our people — they are reckless",
        actor_memory="My attack on {target} caused civilian panic — I'm seen as a threat to stability",
        actor_ego_delta=-0.05,
        actor_radicalization_delta=0.05,
    ),
    ConsequenceOutcome(
        key="target_radicalization",
        description_template="{target} has radicalized their stance after surviving {actor}'s attack!",
        base_weight=0.5,
        actor_exposure_delta=0.2,
        target_trust_delta=-0.9,
        creates_rivalry=True,
        rivalry_intensity=0.9,
        event_visibility=0.6,
        target_memory="{actor} attacked us — we must arm ourselves and prepare for total war",
        target_memory_importance=0.95,
        target_memory_valence=-1.0,
        actor_memory="My attack radicalized {target} — they'll be more dangerous now",
        actor_paranoia_delta=0.2,
    ),
    ConsequenceOutcome(
        key="attacker_exposed",
        description_template="{actor}'s covert attack on {target} was detected — their identity is fully exposed!",
        base_weight=0.8,
        actor_reputation_delta=-0.2,
        actor_exposure_delta=0.6,
        target_trust_delta=-0.8,
        creates_rivalry=True,
        rivalry_intensity=0.7,
        event_visibility=0.8,
        target_memory="{actor} tried to attack us covertly — we now know who they are",
        actor_memory="My attack on {target} was detected — I'm fully exposed now",
        actor_paranoia_delta=0.15,
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="resource_exhaustion",
        description_template="{actor} exhausted significant resources in the failed attack on {target}!",
        base_weight=0.9,
        actor_resources_delta=-0.25,
        actor_power_delta=-0.1,
        event_visibility=0.4,
        actor_memory="My attack on {target} drained my resources for nothing",
        actor_desperation_delta=0.15,
        actor_ego_delta=-0.05,
    ),
]


HOSTILE_TAKEOVER_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="market_panic",
        description_template="{actor}'s failed takeover of {target} triggered market-wide panic!",
        base_weight=0.9,
        actor_resources_delta=-0.2,
        actor_reputation_delta=-0.2,
        event_visibility=1.0,
        target_memory="{actor}'s botched takeover attempt caused market instability — they're desperate",
        actor_memory="My takeover attempt on {target} caused market panic — investors are fleeing",
        actor_fear_delta=0.15,
        actor_ego_delta=-0.15,
    ),
    ConsequenceOutcome(
        key="regulatory_lockout",
        description_template="Regulators blocked {actor}'s takeover of {target} and imposed restrictions!",
        base_weight=0.8,
        actor_power_delta=-0.15,
        actor_resources_delta=-0.1,
        event_visibility=0.9,
        target_memory="Regulators stopped {actor} from taking us over — they're now under scrutiny",
        actor_memory="Regulators blocked my takeover of {target} — I'm now under investigation",
        actor_ego_delta=-0.1,
        delayed_effect={"event_type": "regulatory_investigation", "delay_turns": 3, "description": "Regulators launch an investigation into {actor}'s business practices"},
    ),
    ConsequenceOutcome(
        key="investor_collapse",
        description_template="{actor}'s investors lost confidence after the failed takeover of {target}!",
        base_weight=0.7,
        actor_resources_delta=-0.3,
        actor_power_delta=-0.1,
        event_visibility=0.8,
        actor_memory="My investors are pulling out after the failed takeover of {target}",
        actor_desperation_delta=0.2,
        actor_ego_delta=-0.1,
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="shareholder_revolt",
        description_template="{actor}'s own shareholders revolted after the costly failed takeover of {target}!",
        base_weight=0.6,
        actor_power_delta=-0.2,
        actor_resources_delta=-0.15,
        event_visibility=0.7,
        actor_memory="My shareholders are revolting after the failed takeover — my position is weakened",
        actor_ego_delta=-0.15,
        actor_desperation_delta=0.15,
    ),
    ConsequenceOutcome(
        key="alliance_backlash",
        description_template="{actor}'s allies distanced themselves after the aggressive takeover attempt on {target}!",
        base_weight=0.5,
        actor_reputation_delta=-0.15,
        event_visibility=0.6,
        target_memory="{actor}'s own allies abandoned them after their takeover attempt on us",
        actor_memory="My allies are distancing themselves after the failed takeover of {target}",
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="liquidity_crisis",
        description_template="{actor} burned through cash reserves in the failed takeover — now facing a liquidity crisis!",
        base_weight=0.8,
        actor_resources_delta=-0.35,
        event_visibility=0.5,
        actor_memory="I'm facing a liquidity crisis after the failed takeover of {target}",
        actor_desperation_delta=0.2,
        actor_ego_delta=-0.05,
        actor_radicalization_delta=0.05,
    ),
    ConsequenceOutcome(
        key="public_scandal",
        description_template="{actor}'s hostile takeover attempt on {target} became a public scandal!",
        base_weight=0.7,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.4,
        event_visibility=1.0,
        target_memory="{actor}'s takeover attempt on us became a scandal — public sympathy is with us",
        actor_memory="My takeover attempt on {target} is now a public scandal",
        actor_ego_delta=-0.1,
    ),
]


CAMPAIGN_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="public_backlash",
        description_template="{actor}'s campaign backfired — public opinion shifted against them!",
        base_weight=1.0,
        actor_reputation_delta=-0.2,
        event_visibility=0.9,
        actor_memory="My campaign backfired — the public turned against me",
        actor_ego_delta=-0.1,
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="censorship_crackdown",
        description_template="{actor}'s campaign was censored and suppressed by authorities!",
        base_weight=0.6,
        actor_power_delta=-0.1,
        actor_reputation_delta=-0.1,
        event_visibility=0.5,
        actor_memory="My campaign was censored — I've been silenced by the establishment",
        actor_radicalization_delta=0.1,
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="credibility_collapse",
        description_template="{actor}'s campaign claims were debunked, destroying their credibility!",
        base_weight=0.8,
        actor_reputation_delta=-0.3,
        event_visibility=0.85,
        actor_memory="My campaign was debunked publicly — my credibility is destroyed",
        actor_ego_delta=-0.15,
    ),
    ConsequenceOutcome(
        key="conspiracy_amplification",
        description_template="{actor}'s failed campaign spawned conspiracy theories that overshadowed the real message!",
        base_weight=0.4,
        actor_reputation_delta=-0.1,
        event_visibility=0.7,
        actor_memory="My campaign generated conspiracy theories instead of the intended message",
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="ridicule",
        description_template="{actor}'s campaign became a subject of widespread ridicule and mockery!",
        base_weight=0.7,
        actor_reputation_delta=-0.2,
        event_visibility=0.8,
        actor_memory="My campaign was ridiculed publicly — I'm a laughingstock",
        actor_ego_delta=-0.2,
        actor_desperation_delta=0.05,
    ),
    ConsequenceOutcome(
        key="activist_backlash",
        description_template="Activists turned against {actor}'s campaign, organizing a counter-movement!",
        base_weight=0.5,
        actor_reputation_delta=-0.15,
        actor_power_delta=-0.05,
        event_visibility=0.75,
        actor_memory="Activists organized against my campaign — I've created my own opposition",
        actor_ego_delta=-0.05,
        delayed_effect={"event_type": "counter_movement", "delay_turns": 2, "description": "An organized counter-movement forms against {actor}'s agenda"},
    ),
    ConsequenceOutcome(
        key="propaganda_fatigue",
        description_template="{actor}'s repeated campaigning has caused propaganda fatigue — the public tunes them out!",
        base_weight=0.6,
        actor_reputation_delta=-0.1,
        actor_power_delta=-0.05,
        event_visibility=0.4,
        actor_memory="The public has grown tired of my messaging — I'm being ignored",
        actor_ego_delta=-0.1,
    ),
]


MEDIA_CAMPAIGN_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="credibility_destroyed",
        description_template="{actor}'s media campaign against {target} was exposed as fabricated — credibility destroyed!",
        base_weight=0.9,
        actor_reputation_delta=-0.35,
        actor_exposure_delta=0.4,
        event_visibility=1.0,
        target_memory="{actor}'s media attack on us was proven false — public sympathy is with us now",
        actor_memory="My media campaign against {target} was debunked — I've lost all credibility",
        actor_ego_delta=-0.15,
    ),
    ConsequenceOutcome(
        key="target_sympathy_surge",
        description_template="{actor}'s media attack on {target} backfired — {target} gained public sympathy!",
        base_weight=0.8,
        actor_reputation_delta=-0.2,
        event_visibility=0.9,
        target_memory="{actor} tried to destroy our reputation but the public rallied behind us",
        actor_memory="My media campaign boosted {target}'s popularity instead of destroying it",
        actor_ego_delta=-0.1,
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="legal_retaliation",
        description_template="{target} is filing a defamation lawsuit against {actor} after the failed media campaign!",
        base_weight=0.7,
        actor_resources_delta=-0.15,
        actor_reputation_delta=-0.1,
        event_visibility=0.8,
        target_memory="{actor} ran a false media campaign against us — we're suing them",
        actor_memory="{target} is suing me for defamation after my media campaign backfired",
        actor_fear_delta=0.1,
        delayed_effect={"event_type": "defamation_lawsuit", "delay_turns": 3, "description": "{target} files a major defamation lawsuit against {actor}"},
    ),
    ConsequenceOutcome(
        key="media_blacklist",
        description_template="Media outlets blacklisted {actor} after discovering their campaign against {target} was misleading!",
        base_weight=0.5,
        actor_reputation_delta=-0.25,
        actor_power_delta=-0.1,
        event_visibility=0.7,
        actor_memory="Media outlets blacklisted me after my campaign against {target} was exposed",
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="narrative_backfire",
        description_template="{actor}'s narrative about {target} was turned against them — now {actor} looks like the villain!",
        base_weight=0.8,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.3,
        event_visibility=0.85,
        target_memory="{actor}'s smear campaign backfired — they look like the real villain now",
        actor_memory="My narrative against {target} was flipped — I'm the one being vilified now",
        actor_ego_delta=-0.15,
        actor_paranoia_delta=0.1,
    ),
    ConsequenceOutcome(
        key="whistleblower_exposure",
        description_template="A whistleblower revealed {actor} was behind the media campaign against {target}!",
        base_weight=0.6,
        actor_exposure_delta=0.5,
        actor_reputation_delta=-0.2,
        target_trust_delta=-0.6,
        creates_rivalry=True,
        rivalry_intensity=0.7,
        event_visibility=0.9,
        target_memory="A whistleblower revealed {actor} was orchestrating media attacks against us",
        actor_memory="A whistleblower exposed me as the source of the campaign against {target}",
        actor_paranoia_delta=0.2,
        actor_ego_delta=-0.05,
    ),
]


LOBBYING_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="corruption_exposure",
        description_template="{actor}'s lobbying against {target} was exposed as corrupt influence-peddling!",
        base_weight=0.9,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.5,
        event_visibility=1.0,
        target_memory="{actor} was caught trying to corrupt officials against us",
        actor_memory="My lobbying was exposed as corruption — I'm under public scrutiny",
        actor_ego_delta=-0.1,
        actor_fear_delta=0.15,
        delayed_effect={"event_type": "corruption_investigation", "delay_turns": 3, "description": "Anti-corruption investigators begin probing {actor}'s lobbying activities"},
    ),
    ConsequenceOutcome(
        key="public_outrage",
        description_template="{actor}'s backroom lobbying against {target} triggered public outrage!",
        base_weight=0.8,
        actor_reputation_delta=-0.25,
        actor_exposure_delta=0.3,
        event_visibility=0.9,
        target_memory="The public is outraged at {actor}'s lobbying against us — we have support",
        actor_memory="My lobbying triggered public outrage — I'm toxic now",
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="political_isolation",
        description_template="Politicians distanced themselves from {actor} after the lobbying scandal involving {target}!",
        base_weight=0.7,
        actor_power_delta=-0.2,
        actor_reputation_delta=-0.15,
        event_visibility=0.7,
        actor_memory="Politicians cut ties with me after the lobbying scandal with {target}",
        actor_ego_delta=-0.1,
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="lobby_legal_retaliation",
        description_template="{target} filed legal complaints against {actor} for illegal lobbying practices!",
        base_weight=0.6,
        actor_resources_delta=-0.15,
        actor_exposure_delta=0.3,
        target_trust_delta=-0.7,
        creates_rivalry=True,
        rivalry_intensity=0.6,
        event_visibility=0.8,
        target_memory="{actor} engaged in illegal lobbying against us — we're filing complaints",
        actor_memory="{target} is coming after me legally for my lobbying — this is getting dangerous",
        actor_fear_delta=0.15,
        actor_paranoia_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_hostility",
        description_template="Regulators turned hostile toward {actor} after discovering their lobbying against {target}!",
        base_weight=0.7,
        actor_power_delta=-0.15,
        event_visibility=0.6,
        actor_memory="Regulators are now hostile toward me after my lobbying was discovered",
        actor_fear_delta=0.1,
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="media_humiliation",
        description_template="Media exposed {actor}'s failed lobbying scheme against {target} — public humiliation!",
        base_weight=0.8,
        actor_reputation_delta=-0.3,
        actor_exposure_delta=0.4,
        event_visibility=0.95,
        target_memory="Media humiliated {actor} for their failed lobbying against us",
        actor_memory="The media humiliated me over my lobbying against {target} — I'm a joke",
        actor_ego_delta=-0.2,
        actor_desperation_delta=0.1,
    ),
]


LEGAL_ACTION_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="legal_precedent_against",
        description_template="{actor}'s lawsuit against {target} set a legal precedent that now works against {actor}!",
        base_weight=0.8,
        actor_power_delta=-0.15,
        actor_resources_delta=-0.2,
        event_visibility=0.9,
        target_memory="{actor}'s lawsuit set a precedent in our favor — they weakened their own position",
        actor_memory="My lawsuit against {target} set a precedent that now hurts me",
        actor_ego_delta=-0.1,
        delayed_effect={"event_type": "legal_precedent_cascade", "delay_turns": 4, "description": "The legal precedent from {actor}'s failed case is used against them in new proceedings"},
    ),
    ConsequenceOutcome(
        key="public_sympathy_for_target",
        description_template="{actor}'s legal attack on {target} generated massive public sympathy for {target}!",
        base_weight=0.7,
        actor_reputation_delta=-0.2,
        event_visibility=0.85,
        target_memory="{actor}'s lawsuit made us sympathetic in the public eye",
        actor_memory="My lawsuit made {target} look like a victim — public sympathy is with them",
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="resource_hemorrhage",
        description_template="{actor} hemorrhaged resources on legal fees in the failed case against {target}!",
        base_weight=0.9,
        actor_resources_delta=-0.25,
        event_visibility=0.5,
        actor_memory="My legal battle with {target} drained my resources with no return",
        actor_desperation_delta=0.15,
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="legal_credibility_collapse",
        description_template="{actor}'s frivolous case against {target} destroyed their legal credibility!",
        base_weight=0.6,
        actor_reputation_delta=-0.25,
        actor_power_delta=-0.1,
        event_visibility=0.8,
        actor_memory="My case against {target} was called frivolous — I've lost legal credibility",
        actor_ego_delta=-0.15,
    ),
    ConsequenceOutcome(
        key="regulatory_backlash",
        description_template="Regulators scrutinized {actor}'s legal tactics against {target} and imposed sanctions!",
        base_weight=0.5,
        actor_power_delta=-0.1,
        actor_resources_delta=-0.1,
        event_visibility=0.7,
        actor_memory="Regulators sanctioned me for my legal tactics against {target}",
        actor_fear_delta=0.1,
    ),
    ConsequenceOutcome(
        key="countersuit_filed",
        description_template="{target} filed a devastating countersuit against {actor}!",
        base_weight=0.7,
        actor_resources_delta=-0.15,
        target_trust_delta=-0.5,
        creates_rivalry=True,
        rivalry_intensity=0.6,
        event_visibility=0.8,
        target_memory="{actor} sued us and lost — we're countersuing to make them pay",
        actor_memory="{target} is countersuing me — this legal battle is escalating",
        actor_fear_delta=0.15,
        actor_paranoia_delta=0.1,
        delayed_effect={"event_type": "countersuit", "delay_turns": 2, "description": "{target}'s countersuit against {actor} reaches court"},
    ),
]


ACQUISITION_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="market_confidence_crash",
        description_template="{actor}'s failed acquisition of {target} crashed market confidence in {actor}!",
        base_weight=0.9,
        actor_resources_delta=-0.2,
        actor_reputation_delta=-0.15,
        event_visibility=0.9,
        actor_memory="My failed acquisition of {target} crashed confidence in my organization",
        actor_ego_delta=-0.1,
        actor_desperation_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_block",
        description_template="Regulators formally blocked {actor}'s acquisition of {target} on antitrust grounds!",
        base_weight=0.7,
        actor_power_delta=-0.1,
        actor_resources_delta=-0.1,
        event_visibility=0.85,
        target_memory="Regulators blocked {actor}'s attempt to acquire us — we're protected",
        actor_memory="Regulators blocked my acquisition of {target} — my expansion is stalled",
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="target_empowered",
        description_template="{target} emerged stronger after surviving {actor}'s acquisition attempt — rallying support!",
        base_weight=0.6,
        actor_reputation_delta=-0.1,
        event_visibility=0.7,
        target_memory="{actor} tried to acquire us — we survived and came out stronger",
        actor_memory="My acquisition attempt made {target} stronger — they rallied support",
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="investor_flight",
        description_template="{actor}'s investors fled after the costly failed acquisition of {target}!",
        base_weight=0.8,
        actor_resources_delta=-0.25,
        actor_power_delta=-0.1,
        event_visibility=0.75,
        actor_memory="My investors pulled out after the failed acquisition of {target}",
        actor_desperation_delta=0.2,
        actor_fear_delta=0.1,
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="overextension_exposed",
        description_template="{actor}'s failed acquisition revealed they were dangerously overextended!",
        base_weight=0.7,
        actor_resources_delta=-0.15,
        actor_reputation_delta=-0.1,
        actor_exposure_delta=0.3,
        event_visibility=0.8,
        actor_memory="My failed acquisition exposed how overextended I am — competitors smell blood",
        actor_fear_delta=0.15,
        actor_ego_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="alliance_opportunity_for_target",
        description_template="{target} used {actor}'s failed acquisition as leverage to build new alliances!",
        base_weight=0.5,
        actor_power_delta=-0.05,
        event_visibility=0.6,
        target_memory="{actor}'s acquisition attempt helped us build new alliances — thank them for the motivation",
        actor_memory="{target} turned my acquisition attempt into an alliance opportunity — they're stronger now",
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="acquisition_embarrassment",
        description_template="{actor}'s botched acquisition of {target} became an industry embarrassment!",
        base_weight=0.6,
        actor_reputation_delta=-0.2,
        event_visibility=0.85,
        actor_memory="My failed acquisition of {target} is being mocked across the industry",
        actor_ego_delta=-0.15,
        actor_desperation_delta=0.05,
    ),
]


NEGOTIATION_FAILURE_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="trust_collapse",
        description_template="Trust between {actor} and {target} completely collapsed after the failed negotiation!",
        base_weight=1.0,
        actor_reputation_delta=-0.1,
        target_trust_delta=-0.7,
        event_visibility=0.6,
        target_memory="{actor}'s negotiation revealed they can't be trusted — deal is dead",
        target_memory_importance=0.85,
        target_memory_valence=-0.8,
        actor_memory="Negotiations with {target} collapsed — trust is destroyed",
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="public_embarrassment",
        description_template="{actor}'s negotiation with {target} failed publicly — an embarrassing diplomatic incident!",
        base_weight=0.7,
        actor_reputation_delta=-0.2,
        event_visibility=0.8,
        target_memory="{actor} embarrassed themselves in our negotiations — they're incompetent",
        actor_memory="My negotiation with {target} became a public embarrassment",
        actor_ego_delta=-0.15,
    ),
    ConsequenceOutcome(
        key="faction_disagreement",
        description_template="Internal factions within {actor}'s organization disagreed on terms, torpedoing the negotiation with {target}!",
        base_weight=0.6,
        actor_power_delta=-0.1,
        event_visibility=0.5,
        actor_memory="My own people torpedoed the negotiation with {target} — internal divisions are showing",
        actor_paranoia_delta=0.1,
        actor_ego_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="diplomatic_isolation",
        description_template="{actor}'s failed negotiation with {target} left them diplomatically isolated!",
        base_weight=0.5,
        actor_reputation_delta=-0.15,
        actor_power_delta=-0.1,
        event_visibility=0.65,
        target_memory="{actor} failed to negotiate with us — others are distancing from them too",
        actor_memory="My failed negotiation with {target} left me isolated — no one wants to deal with me",
        actor_ego_delta=-0.1,
        actor_desperation_delta=0.15,
    ),
    ConsequenceOutcome(
        key="opportunistic_betrayal",
        description_template="{target} exploited {actor}'s negotiation overtures to gather intelligence and betray them!",
        base_weight=0.4,
        actor_resources_delta=-0.1,
        actor_exposure_delta=0.3,
        target_trust_delta=-0.9,
        creates_rivalry=True,
        rivalry_intensity=0.7,
        event_visibility=0.5,
        target_memory="{actor} came to negotiate — we used the opportunity to learn their weaknesses",
        actor_memory="{target} betrayed my trust during negotiations — they used it to spy on me",
        actor_paranoia_delta=0.25,
        actor_fear_delta=0.1,
        actor_ego_delta=-0.1,
    ),
]


# Map action families to their FAILURE outcome tables
ACTION_FAMILY_OUTCOMES: Dict[str, List[ConsequenceOutcome]] = {
    "sabotage": SABOTAGE_FAILURE_OUTCOMES,
    "policy": POLICY_FAILURE_OUTCOMES,
    "betrayal": BETRAYAL_FAILURE_OUTCOMES,
    "leak": LEAK_FAILURE_OUTCOMES,
    "attack": ATTACK_FAILURE_OUTCOMES,
    "hostile_takeover": HOSTILE_TAKEOVER_FAILURE_OUTCOMES,
    "campaign": CAMPAIGN_FAILURE_OUTCOMES,
    "media_campaign": MEDIA_CAMPAIGN_FAILURE_OUTCOMES,
    "lobbying": LOBBYING_FAILURE_OUTCOMES,
    "legal_action": LEGAL_ACTION_FAILURE_OUTCOMES,
    "acquisition": ACQUISITION_FAILURE_OUTCOMES,
    "negotiation": NEGOTIATION_FAILURE_OUTCOMES,
}


# ============================================================================
# SUCCESS Outcome Tables
# ============================================================================

SABOTAGE_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="unexplained_accident",
        description_template="{target} suffered an unexplained setback — no one suspects {actor}.",
        base_weight=1.0,
        event_visibility=0.2,
        actor_memory="My sabotage of {target} went perfectly — they suspect nothing",
        actor_memory_valence=0.3,
        target_memory="{target} suffered a mysterious setback with no clear cause",
        target_memory_valence=-0.5,
    ),
    ConsequenceOutcome(
        key="target_paranoia_spike",
        description_template="{target} is growing paranoid after their unexplained losses!",
        base_weight=0.7,
        event_visibility=0.3,
        target_memory="Something is very wrong — our losses feel deliberate but I can't prove it",
        target_memory_importance=0.9,
        target_memory_valence=-0.8,
        actor_memory="My sabotage is making {target} paranoid — they're starting to suspect foul play",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="hidden_retaliation_planned",
        description_template="{target} suspects foul play and is quietly planning countermeasures!",
        base_weight=0.6,
        event_visibility=0.1,
        target_memory="I suspect someone sabotaged us — I'm preparing countermeasures",
        target_memory_importance=0.85,
        target_memory_valence=-0.7,
        actor_memory="I succeeded against {target} but they may be preparing a response",
        actor_paranoia_delta=0.05,
        delayed_effect={
            "event_type": "counter_intelligence",
            "delay_turns": 3,
            "description": "{target} launched counter-intelligence after suspected sabotage",
            "impact_data": {"regulatory_pressure": {"{actor_id}": 0.1}},
        },
    ),
    ConsequenceOutcome(
        key="public_fear_increase",
        description_template="The mysterious damage to {target} is causing public unease!",
        base_weight=0.5,
        event_visibility=0.7,
        actor_memory="My sabotage of {target} has caused wider public fear — more than I intended",
        actor_fear_delta=0.05,
    ),
    ConsequenceOutcome(
        key="cascading_instability",
        description_template="{target}'s losses are cascading through connected systems!",
        base_weight=0.4,
        target_resources_delta=-0.1,
        event_visibility=0.6,
        target_memory="Our setback cascaded — the damage is worse than initially thought",
        target_memory_importance=0.9,
        target_memory_valence=-0.9,
        actor_memory="My sabotage of {target} caused cascading damage — more than planned",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="collateral_damage",
        description_template="{actor}'s sabotage caused unintended collateral damage near {target}!",
        base_weight=0.3,
        actor_reputation_delta=-0.05,
        event_visibility=0.5,
        actor_memory="My sabotage of {target} caused collateral damage — this wasn't planned",
        actor_fear_delta=0.1,
        actor_paranoia_delta=0.05,
    ),
]


ATTACK_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="intimidation_success",
        description_template="{actor}'s attack intimidated {target} and their allies!",
        base_weight=1.0,
        actor_ego_delta=0.1,
        actor_reputation_delta=0.05,
        event_visibility=0.9,
        target_memory="{actor} attacked us and won — we need to be more careful",
        target_memory_valence=-0.8,
        actor_memory="My attack on {target} was a show of force — others took notice",
    ),
    ConsequenceOutcome(
        key="alliance_retaliation_triggered",
        description_template="{target}'s allies are mobilizing in response to {actor}'s attack!",
        base_weight=0.7,
        actor_paranoia_delta=0.1,
        event_visibility=0.8,
        target_memory="{actor} attacked us — our allies are rallying to respond",
        target_memory_valence=-0.7,
        actor_memory="My attack on {target} provoked their allies — I may face retaliation",
        actor_fear_delta=0.1,
        delayed_effect={
            "event_type": "alliance_retaliation",
            "delay_turns": 2,
            "description": "Allies of {target} retaliate against {actor}",
            "impact_data": {"agent_resources": {"{actor_id}": -0.1}},
        },
    ),
    ConsequenceOutcome(
        key="fear_cascade",
        description_template="{actor}'s attack sent a wave of fear through the landscape!",
        base_weight=0.6,
        actor_ego_delta=0.15,
        event_visibility=0.9,
        actor_memory="My attack on {target} caused widespread fear — my reputation grows",
        actor_radicalization_delta=0.05,
    ),
    ConsequenceOutcome(
        key="faction_destabilization",
        description_template="{target}'s faction is fracturing after {actor}'s successful attack!",
        base_weight=0.5,
        target_resources_delta=-0.1,
        event_visibility=0.7,
        target_memory="{actor}'s attack has destabilized our entire faction",
        target_memory_importance=0.9,
        target_memory_valence=-0.9,
        actor_memory="My attack fractured {target}'s faction — they're weaker than ever",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="public_panic",
        description_template="{actor}'s attack on {target} caused public panic!",
        base_weight=0.4,
        actor_reputation_delta=-0.1,
        event_visibility=1.0,
        actor_memory="My attack on {target} caused public panic — this draws unwanted attention",
        actor_fear_delta=0.05,
    ),
    ConsequenceOutcome(
        key="escalation_spiral",
        description_template="{actor}'s attack triggered an escalation spiral with {target}!",
        base_weight=0.5,
        creates_rivalry=True,
        rivalry_intensity=0.9,
        event_visibility=0.8,
        target_memory="{actor} attacked us — this means war",
        target_memory_importance=0.95,
        target_memory_valence=-0.95,
        actor_memory="My attack on {target} has escalated into an ongoing conflict",
        actor_paranoia_delta=0.1,
        actor_radicalization_delta=0.05,
    ),
]


HOSTILE_TAKEOVER_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="investor_panic",
        description_template="{actor}'s takeover of {target} caused investor panic across the sector!",
        base_weight=0.7,
        event_visibility=1.0,
        actor_memory="My takeover of {target} panicked investors — market volatility rising",
        actor_fear_delta=0.05,
    ),
    ConsequenceOutcome(
        key="ego_inflation",
        description_template="{actor} is riding high after seizing {target} — unchecked confidence!",
        base_weight=0.8,
        actor_ego_delta=0.2,
        event_visibility=0.6,
        actor_memory="After taking over {target}, I feel unstoppable",
        actor_memory_valence=0.5,
        actor_desperation_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="market_dominance",
        description_template="{actor} now dominates the market after absorbing {target}!",
        base_weight=1.0,
        actor_power_delta=0.05,
        actor_reputation_delta=0.1,
        event_visibility=0.9,
        actor_memory="My takeover of {target} has given me market dominance",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_scrutiny",
        description_template="Regulators are scrutinizing {actor} after the takeover of {target}!",
        base_weight=0.6,
        event_visibility=0.8,
        actor_memory="Regulators are watching me closely after the {target} takeover",
        actor_paranoia_delta=0.1,
        delayed_effect={
            "event_type": "regulatory_investigation",
            "delay_turns": 3,
            "description": "Regulatory investigation into {actor}'s takeover of {target}",
            "impact_data": {"regulatory_pressure": {"{actor_id}": 0.2}},
        },
    ),
    ConsequenceOutcome(
        key="alliance_fear",
        description_template="Other players fear they could be {actor}'s next target after {target}!",
        base_weight=0.5,
        actor_ego_delta=0.1,
        event_visibility=0.7,
        actor_memory="Others fear being my next target — my power is growing",
        actor_radicalization_delta=0.05,
    ),
    ConsequenceOutcome(
        key="internal_instability",
        description_template="{actor} is struggling to integrate {target}'s operations!",
        base_weight=0.4,
        actor_resources_delta=-0.05,
        actor_power_delta=-0.05,
        event_visibility=0.5,
        actor_memory="Integrating {target} is harder than expected — internal friction rising",
        actor_desperation_delta=0.05,
    ),
]


ACQUISITION_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="market_consolidation",
        description_template="{actor}'s acquisition of {target} consolidated market power!",
        base_weight=1.0,
        actor_power_delta=0.05,
        event_visibility=0.8,
        actor_memory="My acquisition of {target} strengthened my market position",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_attention",
        description_template="Regulators are taking note of {actor}'s growing dominance after acquiring {target}!",
        base_weight=0.7,
        event_visibility=0.7,
        actor_memory="My acquisition of {target} has drawn regulatory attention",
        actor_paranoia_delta=0.05,
        delayed_effect={
            "event_type": "antitrust_review",
            "delay_turns": 3,
            "description": "Antitrust review of {actor}'s acquisition of {target}",
            "impact_data": {"regulatory_pressure": {"{actor_id}": 0.15}},
        },
    ),
    ConsequenceOutcome(
        key="talent_flight",
        description_template="Key talent is fleeing {target} after {actor}'s acquisition!",
        base_weight=0.5,
        target_resources_delta=-0.05,
        event_visibility=0.5,
        actor_memory="Talent is leaving after the {target} acquisition — integration issues",
        actor_desperation_delta=0.05,
    ),
    ConsequenceOutcome(
        key="synergy_gains",
        description_template="{actor} achieved unexpected synergy gains from acquiring {target}!",
        base_weight=0.6,
        actor_resources_delta=0.05,
        actor_power_delta=0.05,
        event_visibility=0.5,
        actor_memory="The {target} acquisition produced synergy gains beyond expectations",
        actor_ego_delta=0.05,
        actor_memory_valence=0.5,
    ),
    ConsequenceOutcome(
        key="competitor_fear",
        description_template="Competitors are consolidating defensively after {actor} acquired {target}!",
        base_weight=0.6,
        event_visibility=0.6,
        actor_memory="My acquisition of {target} has competitors scrambling",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="overextension_risk",
        description_template="{actor} may be overextended after absorbing {target}!",
        base_weight=0.4,
        actor_resources_delta=-0.05,
        event_visibility=0.4,
        actor_memory="I may be overextended after the {target} acquisition",
        actor_desperation_delta=0.05,
        actor_fear_delta=0.05,
    ),
]


MEDIA_CAMPAIGN_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="narrative_dominance",
        description_template="{actor} now controls the narrative about {target}!",
        base_weight=1.0,
        actor_reputation_delta=0.1,
        target_reputation_delta=-0.1,
        event_visibility=0.9,
        actor_memory="I control the public narrative about {target} — powerful position",
        actor_ego_delta=0.1,
        target_memory="{actor}'s media campaign has turned public opinion against us",
        target_memory_valence=-0.8,
    ),
    ConsequenceOutcome(
        key="target_isolation",
        description_template="{target} is being isolated by allies after {actor}'s media campaign!",
        base_weight=0.7,
        target_reputation_delta=-0.15,
        event_visibility=0.8,
        target_memory="We're being isolated — {actor}'s media campaign turned our allies away",
        target_memory_importance=0.9,
        target_memory_valence=-0.9,
        actor_memory="My media campaign against {target} isolated them from allies",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="public_trust_shift",
        description_template="Public trust has shifted dramatically after {actor}'s campaign against {target}!",
        base_weight=0.8,
        event_visibility=1.0,
        actor_memory="Public trust shifted in my favor after my campaign against {target}",
    ),
    ConsequenceOutcome(
        key="media_momentum",
        description_template="{actor}'s media campaign generated self-sustaining momentum!",
        base_weight=0.6,
        actor_reputation_delta=0.05,
        event_visibility=0.7,
        actor_memory="My media campaign against {target} has taken on a life of its own",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="credibility_boost",
        description_template="{actor}'s campaign boosted their own credibility as a truth-teller!",
        base_weight=0.5,
        actor_reputation_delta=0.1,
        event_visibility=0.6,
        actor_memory="My campaign against {target} boosted my own credibility",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="backlash_risk",
        description_template="{actor}'s aggressive media campaign risks a public backlash!",
        base_weight=0.3,
        actor_reputation_delta=-0.05,
        event_visibility=0.5,
        actor_memory="My media campaign against {target} may have gone too far — backlash is possible",
        actor_fear_delta=0.05,
        delayed_effect={
            "event_type": "media_backlash",
            "delay_turns": 2,
            "description": "Public backlash against {actor}'s aggressive media campaign",
            "impact_data": {"public_opinion": {"{actor_id}_credibility": -0.15}},
        },
    ),
]


CAMPAIGN_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="movement_momentum",
        description_template="{actor}'s campaign generated unstoppable momentum!",
        base_weight=1.0,
        actor_reputation_delta=0.1,
        actor_power_delta=0.05,
        event_visibility=0.9,
        actor_memory="My public campaign is gaining unstoppable momentum",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_pressure",
        description_template="{actor}'s campaign forced regulators to take action!",
        base_weight=0.7,
        event_visibility=0.8,
        actor_memory="My campaign forced regulatory action — real change is happening",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="public_awakening",
        description_template="{actor}'s campaign triggered a broad public awakening!",
        base_weight=0.6,
        actor_reputation_delta=0.15,
        event_visibility=1.0,
        actor_memory="My campaign triggered a public awakening — the narrative has shifted",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="opposition_mobilization",
        description_template="{actor}'s campaign success has mobilized organized opposition!",
        base_weight=0.5,
        event_visibility=0.7,
        actor_memory="My campaign succeeded but now organized opposition is forming",
        actor_paranoia_delta=0.1,
        actor_fear_delta=0.05,
        delayed_effect={
            "event_type": "opposition_countermove",
            "delay_turns": 2,
            "description": "Organized opposition mobilized against {actor}'s movement",
            "impact_data": {"public_opinion": {"{actor_id}_support": -0.1}},
        },
    ),
    ConsequenceOutcome(
        key="activist_empowerment",
        description_template="{actor}'s campaign empowered a new generation of activists!",
        base_weight=0.5,
        actor_reputation_delta=0.05,
        event_visibility=0.6,
        actor_memory="My campaign empowered new activists — the movement grows beyond me",
        actor_radicalization_delta=0.05,
    ),
    ConsequenceOutcome(
        key="establishment_fear",
        description_template="The establishment fears {actor}'s growing influence after the campaign!",
        base_weight=0.4,
        actor_ego_delta=0.1,
        event_visibility=0.5,
        actor_memory="The establishment fears my growing influence — they may strike back",
        actor_paranoia_delta=0.05,
    ),
]


LOBBYING_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="political_leverage",
        description_template="{actor} gained critical political leverage against {target}!",
        base_weight=1.0,
        actor_power_delta=0.05,
        event_visibility=0.3,
        actor_memory="I've gained political leverage against {target} through lobbying",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="hidden_influence",
        description_template="{actor} now exerts hidden influence over key decision-makers!",
        base_weight=0.8,
        actor_power_delta=0.05,
        event_visibility=0.2,
        actor_memory="I now have hidden influence over decision-makers — powerful position",
        actor_ego_delta=0.1,
        actor_paranoia_delta=0.05,
    ),
    ConsequenceOutcome(
        key="regulatory_capture",
        description_template="{actor}'s lobbying effectively captured regulatory processes!",
        base_weight=0.5,
        actor_power_delta=0.1,
        event_visibility=0.3,
        actor_memory="I've captured the regulatory process — enormous advantage",
        actor_ego_delta=0.15,
    ),
    ConsequenceOutcome(
        key="exposure_risk",
        description_template="{actor}'s lobbying success leaves a paper trail that could be exposed!",
        base_weight=0.4,
        actor_exposure_delta=0.1,
        event_visibility=0.2,
        actor_memory="My lobbying succeeded but left traces that could be discovered",
        actor_paranoia_delta=0.1,
        actor_fear_delta=0.05,
    ),
    ConsequenceOutcome(
        key="faction_debt",
        description_template="{actor} now owes political favors for their lobbying success!",
        base_weight=0.5,
        event_visibility=0.2,
        actor_memory="My lobbying succeeded but I owe favors — strings are attached",
        actor_desperation_delta=0.05,
    ),
    ConsequenceOutcome(
        key="power_consolidation",
        description_template="{actor} consolidated power through successful lobbying against {target}!",
        base_weight=0.6,
        actor_power_delta=0.05,
        actor_reputation_delta=0.05,
        event_visibility=0.4,
        actor_memory="My lobbying consolidated my power base",
        actor_ego_delta=0.05,
    ),
]


LEGAL_ACTION_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="precedent_set",
        description_template="{actor}'s legal victory set a precedent that weakens {target}'s position!",
        base_weight=1.0,
        actor_reputation_delta=0.1,
        event_visibility=0.9,
        actor_memory="My legal victory set a precedent — {target}'s position is permanently weakened",
        actor_ego_delta=0.1,
        target_memory="{actor}'s legal victory set a dangerous precedent against us",
        target_memory_valence=-0.8,
    ),
    ConsequenceOutcome(
        key="target_crippled",
        description_template="{target} is financially crippled by {actor}'s legal action!",
        base_weight=0.7,
        target_resources_delta=-0.1,
        event_visibility=0.8,
        target_memory="{actor}'s lawsuit has crippled our finances",
        target_memory_importance=0.9,
        target_memory_valence=-0.9,
        actor_memory="My legal action financially crippled {target}",
        actor_ego_delta=0.1,
    ),
    ConsequenceOutcome(
        key="regulatory_cascade",
        description_template="{actor}'s legal win triggered a regulatory cascade affecting {target}!",
        base_weight=0.5,
        event_visibility=0.7,
        actor_memory="My legal victory triggered cascading regulatory action against {target}",
        actor_ego_delta=0.05,
        delayed_effect={
            "event_type": "regulatory_cascade",
            "delay_turns": 2,
            "description": "Regulatory cascade from {actor}'s legal victory against {target}",
            "impact_data": {"regulatory_pressure": {"{target_id}": 0.2}},
        },
    ),
    ConsequenceOutcome(
        key="public_vindication",
        description_template="{actor} was publicly vindicated by the legal victory over {target}!",
        base_weight=0.6,
        actor_reputation_delta=0.15,
        event_visibility=1.0,
        actor_memory="I was publicly vindicated — my reputation is stronger than ever",
        actor_ego_delta=0.15,
        actor_fear_delta=-0.1,
    ),
    ConsequenceOutcome(
        key="legal_momentum",
        description_template="{actor}'s legal win opens the door for further legal action against {target}!",
        base_weight=0.5,
        event_visibility=0.6,
        actor_memory="My legal win opened the door for follow-up actions against {target}",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="overreach_risk",
        description_template="{actor}'s aggressive legal strategy risks being seen as overreach!",
        base_weight=0.3,
        actor_reputation_delta=-0.05,
        event_visibility=0.5,
        actor_memory="My legal strategy may be perceived as overreach — must be careful",
        actor_fear_delta=0.05,
    ),
]


NEGOTIATION_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="mutual_prosperity",
        description_template="{actor} and {target} achieved mutual prosperity through negotiation!",
        base_weight=1.0,
        actor_resources_delta=0.03,
        target_resources_delta=0.03,
        event_visibility=0.5,
        actor_memory="Negotiations with {target} brought mutual prosperity",
        actor_memory_valence=0.5,
        target_memory="Our negotiations with {actor} were genuinely productive",
        target_memory_valence=0.5,
    ),
    ConsequenceOutcome(
        key="trust_deepened",
        description_template="{actor} and {target} deepened their trust through successful negotiation!",
        base_weight=0.8,
        target_trust_delta=0.1,
        event_visibility=0.4,
        actor_memory="My negotiations with {target} deepened our mutual trust",
        actor_memory_valence=0.6,
        target_memory="{actor} proved trustworthy in negotiations — our relationship strengthens",
        target_memory_valence=0.6,
        actor_fear_delta=-0.05,
    ),
    ConsequenceOutcome(
        key="strategic_alignment",
        description_template="{actor} and {target} achieved strategic alignment!",
        base_weight=0.7,
        actor_power_delta=0.03,
        event_visibility=0.5,
        actor_memory="Strategic alignment with {target} gives us both an edge",
        actor_memory_valence=0.4,
    ),
    ConsequenceOutcome(
        key="dependency_created",
        description_template="{target} has become somewhat dependent on {actor} after the deal!",
        base_weight=0.4,
        actor_power_delta=0.05,
        event_visibility=0.3,
        actor_memory="{target} is becoming dependent on our arrangement — leverage",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="reputation_boost",
        description_template="{actor}'s successful negotiation boosted their reputation as a dealmaker!",
        base_weight=0.6,
        actor_reputation_delta=0.05,
        event_visibility=0.5,
        actor_memory="My successful negotiation with {target} boosted my dealmaker reputation",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="complacency_risk",
        description_template="{actor} may be growing complacent after the easy negotiation with {target}!",
        base_weight=0.3,
        event_visibility=0.2,
        actor_memory="The negotiation with {target} was easy — perhaps too easy",
        actor_ego_delta=0.1,
        actor_paranoia_delta=-0.05,
    ),
]


TALENT_SUCCESS_OUTCOMES: List[ConsequenceOutcome] = [
    ConsequenceOutcome(
        key="capability_surge",
        description_template="{actor} gained a major capability surge from poaching {target}'s talent!",
        base_weight=1.0,
        actor_power_delta=0.05,
        event_visibility=0.5,
        actor_memory="Poaching {target}'s talent gave us a significant capability boost",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="target_brain_drain",
        description_template="{target} is suffering a brain drain after {actor}'s talent raid!",
        base_weight=0.7,
        target_resources_delta=-0.05,
        target_reputation_delta=-0.05,
        event_visibility=0.6,
        target_memory="{actor} is draining our talent — we're losing key people",
        target_memory_importance=0.85,
        target_memory_valence=-0.8,
        actor_memory="I'm causing a brain drain at {target} — their loss is my gain",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="innovation_leap",
        description_template="{actor}'s new talent acquisition produced an innovation leap!",
        base_weight=0.5,
        actor_power_delta=0.05,
        event_visibility=0.4,
        actor_memory="The talent I acquired from {target} produced an innovation breakthrough",
        actor_ego_delta=0.1,
        actor_memory_valence=0.5,
    ),
    ConsequenceOutcome(
        key="loyalty_concerns",
        description_template="{actor}'s existing team is uneasy about the new talent from {target}!",
        base_weight=0.4,
        event_visibility=0.3,
        actor_memory="My existing team is uneasy about the talent poached from {target}",
        actor_paranoia_delta=0.05,
        actor_fear_delta=0.05,
    ),
    ConsequenceOutcome(
        key="competitive_edge",
        description_template="{actor} gained a competitive edge over {target} through talent acquisition!",
        base_weight=0.8,
        event_visibility=0.5,
        actor_memory="I now have a competitive edge over {target} thanks to their former talent",
        actor_ego_delta=0.05,
    ),
    ConsequenceOutcome(
        key="internal_friction",
        description_template="{actor} is experiencing internal friction integrating {target}'s former talent!",
        base_weight=0.3,
        actor_resources_delta=-0.03,
        event_visibility=0.3,
        actor_memory="Integrating talent from {target} is causing internal friction",
        actor_desperation_delta=0.05,
    ),
]


# Map action families to their SUCCESS outcome tables
ACTION_FAMILY_SUCCESS_OUTCOMES: Dict[str, List[ConsequenceOutcome]] = {
    "sabotage": SABOTAGE_SUCCESS_OUTCOMES,
    "attack": ATTACK_SUCCESS_OUTCOMES,
    "hostile_takeover": HOSTILE_TAKEOVER_SUCCESS_OUTCOMES,
    "acquisition": ACQUISITION_SUCCESS_OUTCOMES,
    "media_campaign": MEDIA_CAMPAIGN_SUCCESS_OUTCOMES,
    "campaign": CAMPAIGN_SUCCESS_OUTCOMES,
    "lobbying": LOBBYING_SUCCESS_OUTCOMES,
    "legal_action": LEGAL_ACTION_SUCCESS_OUTCOMES,
    "negotiation": NEGOTIATION_SUCCESS_OUTCOMES,
    "talent": TALENT_SUCCESS_OUTCOMES,
}


# ============================================================================
# Weight Adjustment Rules
# ============================================================================


def _compute_weight_multipliers(
    outcome: ConsequenceOutcome,
    ctx: ConsequenceContext,
) -> float:
    """
    Compute a context-driven weight multiplier for a single outcome.

    This is the heart of the contextual branching: specific context
    combinations amplify or suppress specific outcome probabilities.
    """
    multiplier = 1.0

    # ── Paranoia amplifies retaliation and paranoia outcomes ──
    if outcome.key in ("retaliation_escalation", "retaliation_planning", "paranoia_spike"):
        multiplier *= 1.0 + (ctx.paranoia * 2.0)  # high paranoia → 3x

    # ── High visibility amplifies exposure outcomes ──
    if outcome.actor_exposure_delta > 0:
        multiplier *= 1.0 + (ctx.actor_visibility * 1.5)  # visible actors get exposed more

    if outcome.key in ("exposed_operative", "source_discovery", "social_isolation"):
        multiplier *= 1.0 + (ctx.actor_visibility * 2.0)

    # ── Scarcity amplifies resource drain and desperation outcomes ──
    if outcome.key in ("resource_drain", "loyalty_collapse"):
        multiplier *= 1.0 + (ctx.global_scarcity * 1.5)

    if outcome.actor_resources_delta < 0:
        multiplier *= 1.0 + (ctx.global_scarcity * 1.0)

    # ── Low trust amplifies betrayal/distrust outcomes ──
    if outcome.key in ("alliance_distrust", "faction_fracture", "faction_disagreement"):
        multiplier *= 1.0 + ((1.0 - ctx.target_trust) * 1.5)

    # ── High public fear amplifies panic and media outcomes ──
    if outcome.key in ("public_panic", "public_backlash", "media_humiliation"):
        multiplier *= 1.0 + (ctx.public_fear * 2.0)

    # ── Desperation amplifies desperation-escalating outcomes ──
    if outcome.actor_desperation_delta > 0:
        multiplier *= 1.0 + (ctx.desperation * 1.0)

    # ── Prior betrayals amplify betrayal-related retaliation ──
    if outcome.key in ("retaliation_planning", "blackmail", "loyalty_collapse"):
        multiplier *= 1.0 + (min(ctx.recent_betrayals, 3) * 0.5)

    # ── Ally betrayal has stronger consequences ──
    if ctx.is_ally and outcome.creates_rivalry:
        multiplier *= 1.5

    # ── High ego amplifies humiliation outcomes ──
    if outcome.key in ("media_humiliation", "social_isolation", "credibility_erosion"):
        multiplier *= 1.0 + (ctx.ego * 1.0)

    # ── World instability amplifies escalation ──
    if outcome.key in ("retaliation_escalation", "conspiracy_amplification", "public_panic"):
        multiplier *= 1.0 + (ctx.world_instability * 1.5)

    # ── Consecutive failures amplify desperation and fear outcomes ──
    if ctx.consecutive_failures >= 2:
        if outcome.actor_fear_delta > 0 or outcome.actor_desperation_delta > 0:
            multiplier *= 1.0 + (ctx.consecutive_failures * 0.3)

    return multiplier


def _compute_success_weight_multipliers(
    outcome: ConsequenceOutcome,
    ctx: ConsequenceContext,
) -> float:
    """
    Compute a context-driven weight multiplier for a SUCCESS outcome.

    Success-specific context rules determine which secondary effects
    are more likely given the current world state.
    """
    multiplier = 1.0

    # ── High ego amplifies ego-inflating and overconfidence outcomes ──
    if outcome.actor_ego_delta > 0.05:
        multiplier *= 1.0 + (ctx.ego * 1.5)  # already-high ego → more ego inflation

    if outcome.key in ("ego_inflation", "complacency_risk", "overextension_risk"):
        multiplier *= 1.0 + (ctx.ego * 2.0)

    # ── High visibility amplifies public-facing success outcomes ──
    if outcome.key in ("narrative_dominance", "public_vindication", "public_awakening",
                        "public_trust_shift", "intimidation_success", "movement_momentum"):
        multiplier *= 1.0 + (ctx.actor_visibility * 1.5)

    # ── Low scarcity amplifies expansion/consolidation ──
    if outcome.key in ("market_dominance", "market_consolidation", "synergy_gains",
                        "power_consolidation", "strategic_alignment"):
        multiplier *= 1.0 + ((1.0 - ctx.global_scarcity) * 1.0)

    # ── High scarcity amplifies fear/panic outcomes ──
    if outcome.key in ("investor_panic", "alliance_fear", "public_panic",
                        "public_fear_increase", "establishment_fear"):
        multiplier *= 1.0 + (ctx.global_scarcity * 2.0)

    # ── World instability amplifies escalation and destabilization ──
    if outcome.key in ("escalation_spiral", "faction_destabilization", "cascading_instability",
                        "internal_instability", "fear_cascade"):
        multiplier *= 1.0 + (ctx.world_instability * 1.5)

    # ── Prior betrayals amplify retaliation-triggering outcomes ──
    if outcome.key in ("alliance_retaliation_triggered", "hidden_retaliation_planned",
                        "opposition_mobilization"):
        multiplier *= 1.0 + (min(ctx.recent_betrayals, 3) * 0.5)

    # ── Target being an ally amplifies trust and dependency outcomes ──
    if ctx.is_ally and outcome.key in ("trust_deepened", "mutual_prosperity",
                                        "dependency_created", "strategic_alignment"):
        multiplier *= 1.5

    # ── High resources amplifies overextension/complacency risks ──
    if outcome.key in ("overextension_risk", "complacency_risk", "internal_friction"):
        multiplier *= 1.0 + (ctx.actor_resources * 1.0)

    # ── High reputation amplifies regulatory scrutiny ──
    if outcome.key in ("regulatory_scrutiny", "regulatory_attention", "regulatory_capture",
                        "exposure_risk"):
        multiplier *= 1.0 + (ctx.actor_reputation * 1.0)

    # ── Rival target amplifies intimidation and fear outcomes ──
    if ctx.is_rival and outcome.key in ("intimidation_success", "target_brain_drain",
                                         "target_isolation", "target_crippled"):
        multiplier *= 1.3

    # ── High paranoia amplifies paranoia-related outcomes even on success ──
    if outcome.key in ("target_paranoia_spike", "exposure_risk", "loyalty_concerns"):
        multiplier *= 1.0 + (ctx.paranoia * 1.0)

    # ── Active alliances amplify alliance-related retaliation ──
    if outcome.key in ("alliance_retaliation_triggered", "alliance_fear"):
        multiplier *= 1.0 + (ctx.active_alliances * 0.2)

    return multiplier


# ============================================================================
# Engine
# ============================================================================


class ContextualConsequenceEngine:
    """
    Contextual consequence resolution engine.

    Replaces static failure templates with context-driven, weighted
    outcome branching that mutates persistent systems and creates
    lasting memories.
    """

    # ── Context Building ──

    async def build_context(
        self,
        db: AsyncSession,
        agent: Agent,
        target: Optional[Agent],
        structured: StructuredWorldState,
    ) -> ConsequenceContext:
        """
        Build a ConsequenceContext from the current world state, agent
        psychology, relationship state, and recent history.
        """
        agent_id_str = str(agent.id)

        # Agent psychology
        psych_dict = agent.mutable_psychology or {}
        psych = MutablePsychology(**psych_dict) if psych_dict else MutablePsychology()

        # Relationship state
        target_trust = 0.5
        rel_strength = 0.0
        is_ally = False
        is_rival = False

        if target:
            target_id_str = str(target.id)
            rel_manager = RelationshipManager(agent.id)
            relationship = await rel_manager.get_relationship(db, target.id)
            if relationship:
                target_trust = relationship.trust
                rel_strength = relationship.strength
                is_ally = relationship.relationship_type in ("ally", "friend", "partner")
                is_rival = relationship.relationship_type in ("enemy", "rival")
            else:
                # Check structured alliances
                is_ally = any(
                    (a.agent_a == agent_id_str and a.agent_b == target_id_str) or
                    (a.agent_b == agent_id_str and a.agent_a == target_id_str)
                    for a in structured.alliances
                )
                is_rival = any(
                    (r.agent_a == agent_id_str and r.agent_b == target_id_str) or
                    (r.agent_b == agent_id_str and r.agent_a == target_id_str)
                    for r in structured.rivalries
                )

        # Public context
        actor_visibility = structured.agent_exposure.get(agent_id_str, 0.0)
        actor_reputation = structured.agent_reputation.get(agent_id_str, 0.5)

        # Public fear (average negative public opinion)
        negative_opinions = [v for v in structured.public_opinion.values() if v > 0.6]
        public_fear = sum(negative_opinions) / max(len(negative_opinions), 1) if negative_opinions else 0.0

        # Resources
        actor_resources = structured.agent_resources.get(agent_id_str, 0.5)
        target_resources = 0.5
        if target:
            target_resources = structured.agent_resources.get(str(target.id), 0.5)

        # Global scarcity (inverse of average resource level)
        all_resources = list(structured.agent_resources.values())
        avg_resources = sum(all_resources) / max(len(all_resources), 1) if all_resources else 0.5
        global_scarcity = max(0.0, min(1.0, 1.0 - avg_resources))

        # Count recent betrayals from events
        recent_betrayals = sum(
            1 for e in structured.recent_events
            if "betray" in e.action.lower() or "sabotage_exposed" in e.action.lower()
        )

        # World instability
        instability = min(1.0, (
            len(structured.rivalries) * 0.1 +
            global_scarcity * 0.3 +
            public_fear * 0.3 +
            sum(1 for e in structured.recent_events if e.visibility > 0.7) * 0.05
        ))

        # Recent action history
        actor_recent_actions = [
            e.action for e in structured.recent_events
            if e.actor == agent.name
        ][-5:]

        return ConsequenceContext(
            paranoia=psych.paranoia,
            fear=psych.fear,
            ego=psych.ego,
            greed=psych.greed,
            desperation=psych.desperation,
            radicalization=psych.radicalization,
            consecutive_failures=psych.consecutive_failures,
            target_trust=target_trust,
            relationship_strength=rel_strength,
            is_ally=is_ally,
            is_rival=is_rival,
            actor_visibility=actor_visibility,
            actor_reputation=actor_reputation,
            public_fear=public_fear,
            actor_resources=actor_resources,
            target_resources=target_resources,
            global_scarcity=global_scarcity,
            recent_betrayals=recent_betrayals,
            recent_failures_total=sum(
                1 for e in structured.recent_events if "failed" in e.action.lower()
            ),
            world_instability=instability,
            active_rivalries=len(structured.rivalries),
            active_alliances=len(structured.alliances),
            actor_recent_actions=actor_recent_actions,
            tension=getattr(structured, 'tension', 0.0),
        )

    # ── Consequence Resolution ──

    def resolve_failure(
        self,
        action_family: str,
        agent: Agent,
        target: Optional[Agent],
        ctx: ConsequenceContext,
    ) -> Tuple[ConsequenceOutcome, str]:
        """
        Resolve a failure into a contextually weighted consequence.

        Args:
            action_family: One of "sabotage", "policy", "betrayal", "leak"
            agent: The acting agent
            target: The target agent (may be None for self-targeting actions)
            ctx: The built ConsequenceContext

        Returns:
            Tuple of (selected outcome, formatted description)
        """
        outcomes = ACTION_FAMILY_OUTCOMES.get(action_family, SABOTAGE_FAILURE_OUTCOMES)

        # Compute weighted probabilities
        weighted: List[Tuple[ConsequenceOutcome, float]] = []
        for outcome in outcomes:
            weight = outcome.base_weight * _compute_weight_multipliers(outcome, ctx)
            weighted.append((outcome, weight))

        # Apply Tension modifiers (catastrophic shift, panic amplification, etc)
        weighted = TensionModifierSystem.apply_to_consequence_weights(weighted, ctx.tension)

        # Normalize weights into probabilities
        total_weight = sum(w for _, w in weighted)
        if total_weight == 0:
            total_weight = 1.0  # safety

        probabilities = [w / total_weight for _, w in weighted]

        # Weighted random selection
        selected = random.choices(
            [o for o, _ in weighted],
            weights=probabilities,
            k=1,
        )[0]

        # Format description
        actor_name = agent.name
        target_name = target.name if target else "unknown"
        description = selected.description_template.format(
            actor=actor_name, target=target_name
        )

        logger.info(
            f"Contextual consequence resolved: {action_family} → {selected.key} "
            f"(paranoia={ctx.paranoia:.2f}, visibility={ctx.actor_visibility:.2f}, "
            f"scarcity={ctx.global_scarcity:.2f}, trust={ctx.target_trust:.2f})"
        )

        return selected, description

    def resolve_success(
        self,
        action_family: str,
        agent: Agent,
        target: Optional[Agent],
        ctx: ConsequenceContext,
    ) -> Tuple[ConsequenceOutcome, str]:
        """
        Resolve a SUCCESS into contextually weighted secondary effects.

        This produces the *additional* contextual consequence that occurs
        alongside the base success logic (resource/power changes). It
        determines what ripple effects the success causes based on context.

        Args:
            action_family: One of the registered success families
            agent: The acting agent
            target: The target agent (may be None for self-targeting actions)
            ctx: The built ConsequenceContext

        Returns:
            Tuple of (selected outcome, formatted description)
        """
        outcomes = ACTION_FAMILY_SUCCESS_OUTCOMES.get(action_family)
        if not outcomes:
            # No success table for this family — return a neutral outcome
            return ConsequenceOutcome(
                key="standard_success",
                description_template="{actor}'s action succeeded as expected.",
                base_weight=1.0,
            ), f"{agent.name}'s action succeeded as expected."

        # Compute weighted probabilities
        weighted: List[Tuple[ConsequenceOutcome, float]] = []
        for outcome in outcomes:
            weight = outcome.base_weight * _compute_success_weight_multipliers(outcome, ctx)
            weighted.append((outcome, weight))

        # Apply Tension modifiers
        weighted = TensionModifierSystem.apply_to_consequence_weights(weighted, ctx.tension)

        # Normalize weights into probabilities
        total_weight = sum(w for _, w in weighted)
        if total_weight == 0:
            total_weight = 1.0

        probabilities = [w / total_weight for _, w in weighted]

        # Weighted random selection
        selected = random.choices(
            [o for o, _ in weighted],
            weights=probabilities,
            k=1,
        )[0]

        # Format description
        actor_name = agent.name
        target_name = target.name if target else "unknown"
        description = selected.description_template.format(
            actor=actor_name, target=target_name
        )

        logger.info(
            f"Contextual SUCCESS resolved: {action_family} → {selected.key} "
            f"(ego={ctx.ego:.2f}, visibility={ctx.actor_visibility:.2f}, "
            f"scarcity={ctx.global_scarcity:.2f}, instability={ctx.world_instability:.2f})"
        )

        return selected, description

    # ── Secondary Effects ──

    async def apply_secondary_effects(
        self,
        db: AsyncSession,
        agent: Agent,
        target: Optional[Agent],
        outcome: ConsequenceOutcome,
        structured: StructuredWorldState,
        simulation_step: int,
        world_state: Optional[WorldState] = None,
    ) -> None:
        """
        Apply persistent secondary effects from a consequence outcome:
        - Mutate world state (reputation, exposure, resources, power)
        - Mutate agent psychology
        - Create/update rivalries
        - Record memories
        - Schedule delayed effects
        """
        agent_id_str = str(agent.id)

        # ── World state mutations ──
        if outcome.actor_reputation_delta != 0:
            structured.agent_reputation[agent_id_str] = max(0.0, min(1.0,
                structured.agent_reputation.get(agent_id_str, 0.5) + outcome.actor_reputation_delta
            ))

        if outcome.actor_exposure_delta != 0:
            structured.agent_exposure[agent_id_str] = max(0.0, min(1.0,
                structured.agent_exposure.get(agent_id_str, 0.0) + outcome.actor_exposure_delta
            ))

        if outcome.actor_resources_delta != 0:
            structured.agent_resources[agent_id_str] = max(0.02, min(1.0,
                structured.agent_resources.get(agent_id_str, 0.5) + outcome.actor_resources_delta
            ))

        if outcome.actor_power_delta != 0:
            structured.agent_power[agent_id_str] = max(0.0, min(1.0,
                structured.agent_power.get(agent_id_str, 0.5) + outcome.actor_power_delta
            ))

        if target and outcome.target_resources_delta != 0:
            target_id_str = str(target.id)
            structured.agent_resources[target_id_str] = max(0.02, min(1.0,
                structured.agent_resources.get(target_id_str, 0.5) + outcome.target_resources_delta
            ))

        if target and outcome.target_reputation_delta != 0:
            target_id_str = str(target.id)
            structured.agent_reputation[target_id_str] = max(0.0, min(1.0,
                structured.agent_reputation.get(target_id_str, 0.5) + outcome.target_reputation_delta
            ))

        # ── Relationship mutation ──
        if target and outcome.target_trust_delta != 0:
            rel_manager = RelationshipManager(target.id)
            await rel_manager.record_interaction(
                db,
                project_id=world_state.project_id if world_state else agent.project_id,
                other_agent_id=agent.id,
                interaction_type="betrayal" if outcome.target_trust_delta < -0.5 else "conflict",
                description=f"Consequence of {agent.name}'s failed action: {outcome.key}",
                outcome="negative",
                trust_change=outcome.target_trust_delta,
                strength_change=min(0, outcome.target_trust_delta * 0.5),
            )

        # ── Rivalry creation ──
        if target and outcome.creates_rivalry:
            target_id_str = str(target.id)
            # Check if rivalry already exists
            existing = any(
                {r.agent_a, r.agent_b} == {agent_id_str, target_id_str}
                for r in structured.rivalries
            )
            if not existing:
                structured.rivalries.append(RivalryRecord(
                    agent_a=target_id_str,
                    agent_b=agent_id_str,
                    started_at_step=simulation_step,
                    intensity=outcome.rivalry_intensity,
                    cause=outcome.key,
                ))
            else:
                # Intensify existing rivalry
                for r in structured.rivalries:
                    if {r.agent_a, r.agent_b} == {agent_id_str, target_id_str}:
                        r.intensity = min(1.0, r.intensity + 0.2)
                        break

        # ── Psychology mutation ──
        psych_dict = agent.mutable_psychology or {}
        psych = MutablePsychology(**psych_dict) if psych_dict else MutablePsychology()
        
        tension = getattr(structured, 'tension', 0.0)

        if outcome.actor_paranoia_delta:
            delta = apply_tension_to_psychology_delta(outcome.actor_paranoia_delta, tension, "paranoia")
            psych.paranoia = max(0.0, min(1.0, psych.paranoia + delta))
        if outcome.actor_fear_delta:
            delta = apply_tension_to_psychology_delta(outcome.actor_fear_delta, tension, "fear")
            psych.fear = max(0.0, min(1.0, psych.fear + delta))
        if outcome.actor_desperation_delta:
            delta = apply_tension_to_psychology_delta(outcome.actor_desperation_delta, tension, "desperation")
            psych.desperation = max(0.0, min(1.0, psych.desperation + delta))
        if outcome.actor_ego_delta:
            delta = apply_tension_to_psychology_delta(outcome.actor_ego_delta, tension, "ego")
            psych.ego = max(0.0, min(1.0, psych.ego + delta))
        if outcome.actor_radicalization_delta:
            delta = apply_tension_to_psychology_delta(outcome.actor_radicalization_delta, tension, "radicalization")
            psych.radicalization = max(0.0, min(1.0, psych.radicalization + delta))

        agent.mutable_psychology = psych.model_dump()
        db.add(agent)

        # ── Memory recording ──
        actor_name = agent.name
        target_name = target.name if target else "unknown"

        if outcome.target_memory and target:
            await self._record_memory(
                db,
                agent_id=target.id,
                content=outcome.target_memory.format(actor=actor_name, target=target_name),
                importance=outcome.target_memory_importance,
                valence=outcome.target_memory_valence,
                related_agents=[agent.id],
            )

        if outcome.actor_memory:
            await self._record_memory(
                db,
                agent_id=agent.id,
                content=outcome.actor_memory.format(actor=actor_name, target=target_name),
                importance=outcome.actor_memory_importance,
                valence=outcome.actor_memory_valence,
                related_agents=[target.id] if target else [],
            )

        # ── Event logging ──
        structured.recent_events.append(WorldEventRecord(
            step=simulation_step,
            actor=actor_name,
            action=f"{outcome.key}",
            target=target_name if target else None,
            outcome=outcome.description_template.format(actor=actor_name, target=target_name),
            visibility=outcome.event_visibility,
        ))

        # ── Delayed effects ──
        if outcome.delayed_effect and world_state:
            from backend.systems.delayed_effect_system import DelayedEffectSystem
            delayed_system = DelayedEffectSystem()
            delay_data = outcome.delayed_effect.copy()
            delay_turns = delay_data.pop("delay_turns", 2)

            # Template substitution in delayed effect data
            desc = delay_data.get("description", "")
            desc = desc.format(actor=actor_name, target=target_name)
            delay_data["description"] = desc

            # Handle impact_data template substitution
            impact_data = delay_data.get("impact_data", {})
            substituted = {}
            for key, value in impact_data.items():
                if isinstance(value, dict):
                    new_value = {}
                    for k, v in value.items():
                        new_k = k.replace("{actor_id}", agent_id_str)
                        if target:
                            new_k = new_k.replace("{target_id}", str(target.id))
                        new_value[new_k] = v
                    substituted[key] = new_value
                else:
                    substituted[key] = value
            delay_data["impact_data"] = substituted

            await delayed_system.schedule(
                db=db,
                project_id=world_state.project_id,
                trigger_turn=simulation_step + delay_turns,
                event_type=delay_data.get("event_type", "delayed_consequence"),
                description=desc,
                impact_data=substituted,
            )

    # ── Helper: Record Memory ──

    async def _record_memory(
        self,
        db: AsyncSession,
        agent_id: UUID,
        content: str,
        importance: float,
        valence: float,
        related_agents: Optional[List[UUID]] = None,
    ) -> None:
        """Record a consequence memory for an agent."""
        try:
            memory_mgr = AgentMemoryManager(agent_id)
            await memory_mgr.remember(
                db,
                memory_type="discovery",
                content=content,
                importance=importance,
                emotional_valence=valence,
                related_agents=related_agents,
            )
        except Exception as e:
            logger.error(f"Failed to record consequence memory for agent {agent_id}: {e}")
