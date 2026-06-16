import random
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.world_models import WorldState, StructuredWorldState, WorldEventRecord
from backend.systems.public_opinion_system import PublicOpinionSystem

class BlackSwanSystem:
    """
    Manages rare, highly impactful events that can disrupt equilibrium.
    """

    # Impact maps to StructuredWorldState dicts
    EVENTS = [
        {
            "name": "anomaly_event_1",
            "description": "A massive, unexplained anomaly disrupts the primary resource network.",
            "probability": 0.001,
            "impact": {"market_conditions": {"sector_1": -0.8, "sector_2": -0.6}, "public_opinion": {"trust_in_authorities": -0.5}}
        },
        {
            "name": "anomaly_event_2",
            "description": "A charismatic entity has spawned a mass movement overnight.",
            "probability": 0.005,
            "impact": {"public_opinion": {"trust_in_authorities": +0.4, "social_stability": -0.3}}
        },
        {
            "name": "anomaly_event_3",
            "description": "A rogue actor has seized significant infrastructural assets.",
            "probability": 0.002,
            "impact": {"market_conditions": {"sector_1": -0.5}, "public_opinion": {"geopolitical_tension": +0.6}}
        },
        {
            "name": "anomaly_event_4",
            "description": "A surprise technological breakthrough renders current defenses obsolete.",
            "probability": 0.001,
            "impact": {"market_conditions": {"sector_3": -0.9, "sector_1": +0.4}, "regulatory_pressure": {"sector_1": +0.8}}
        },
        {
            "name": "anomaly_event_5",
            "description": "A natural disaster has knocked out major supply chains.",
            "probability": 0.0005,
            "impact": {"market_conditions": {"sector_2": -0.8, "sector_1": -0.7}}
        },
        {
            "name": "anomaly_event_6",
            "description": "A fringe group's open-source tool went viral and now controls a fanatical cult.",
            "probability": 0.008,
            "impact": {"public_opinion": {"trust_in_authorities": -0.5, "social_stability": -0.4}, "regulatory_pressure": {"open_source": +0.7}}
        },
    ]

    def __init__(self):
        self.public_opinion_system = PublicOpinionSystem()

    def roll(
        self,
        world_state: WorldState,
        current_step: int,
        project_id: UUID,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Call once per simulation step. Rolls for all events.
        If one fires, it mutates the state immediately and returns the event payload.
        """
        if not world_state or not world_state.state:
            return None

        structured = self._get_structured_state(world_state)
        event_fired = None

        for ev in self.EVENTS:
            if random.random() < ev["probability"]:
                logger.warning(f"BLACK SWAN EVENT FIRED: {ev['name']}")
                self._fire_event(ev, structured, current_step)
                event_fired = ev
                break  # Only one black swan per step maximum

        if event_fired:
            self._save_structured_state(world_state, structured)
            db.add(world_state)
            # The caller (simulation_engine) will handle committing it later.

        return event_fired

    def _fire_event(self, ev: Dict[str, Any], structured: StructuredWorldState, current_step: int):
        """Applies the event impacts and logs it as a highly visible world event."""
        impact_data = ev["impact"]
        extra_events = []

        # Apply impacts
        if "public_opinion" in impact_data:
            for topic, delta in impact_data["public_opinion"].items():
                event_msg = self.public_opinion_system.push_opinion(structured, topic, delta)
                if event_msg:
                    extra_events.append(event_msg)

        if "market_conditions" in impact_data:
            for sector, delta in impact_data["market_conditions"].items():
                current = structured.market_conditions.get(sector, 0.5)
                structured.market_conditions[sector] = max(0.0, min(1.0, current + delta))

        if "regulatory_pressure" in impact_data:
            for entity, delta in impact_data["regulatory_pressure"].items():
                current = structured.regulatory_pressure.get(entity, 0.0)
                structured.regulatory_pressure[entity] = max(0.0, min(1.0, current + delta))

        # Log the primary event
        structured.recent_events.append(WorldEventRecord(
            step=current_step,
            actor="universe",
            action="black_swan",
            outcome=f"BLACK SWAN: {ev['description']}",
            visibility=1.0  # Everyone sees a black swan
        ))

        # Log any tipping points caused by the event
        for extra in extra_events:
            structured.recent_events.append(WorldEventRecord(
                step=current_step,
                actor="system",
                action="opinion_shift",
                outcome=extra,
                visibility=1.0
            ))

    def _get_structured_state(self, world_state: WorldState) -> StructuredWorldState:
        """Get or create structured world state"""
        if isinstance(world_state.state, dict) and "agent_resources" in world_state.state:
            return StructuredWorldState.from_dict(world_state.state)
        return StructuredWorldState.from_legacy_state(world_state.state)

    def _save_structured_state(self, world_state: WorldState, structured: StructuredWorldState):
        """Save structured state back to WorldState object"""
        world_state.state = structured.to_dict()
