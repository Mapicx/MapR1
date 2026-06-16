"""Persistent World Economy + Resource Scarcity"""
import random
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models.economy_models import GlobalEconomyState, ResourceType
from backend.models.world_models import StructuredWorldState, WorldEventRecord
from backend.models.action_models import AgentAction, ActionType


class EconomySystem:
    """Updates global economy and resource scarcity each simulation step."""

    def __init__(self):
        self.resources = [r.value for r in ResourceType]
        self.scarcity_multiplier = 1.0  # 1.0 = normal, rises as things get rarer

        # Deterministic cost/impact mapping for each ActionType
        self.action_impacts = {
            # Economic
            ActionType.EXPAND_BUSINESS.value: {"resource_1": -2000, "displaced_units": 50000, "confidence": 0.01},
            ActionType.LAUNCH_PRODUCT.value: {"resource_1": -1000, "resource_2": -500, "displaced_units": 10000},
            ActionType.ACQUIRE_COMPANY.value: {"confidence": 0.03},
            ActionType.INVEST.value: {"confidence": 0.02, "gdp_growth": 0.005},
            ActionType.HOSTILE_TAKEOVER.value: {"confidence": -0.05, "gdp_growth": -0.002},
            ActionType.POACH_TALENT.value: {"confidence": -0.01},
            ActionType.BID_ON_CONTRACT.value: {"resource_1": -500, "resource_2": -200},
            
            # Technology/AI specific (we map INNOVATE/RESEARCH here)
            ActionType.INNOVATE.value: {"resource_1": -5000, "resource_2": -2000},
            ActionType.RESEARCH.value: {"resource_1": -3000, "resource_2": -1000},
            
            # Political & Social
            ActionType.PROPOSE_POLICY.value: {"confidence": 0.01},
            ActionType.IMPOSE_SANCTIONS.value: {"confidence": -0.05, "gdp_growth": -0.01, "resource_3_supply": -500},
            ActionType.LOBBY_INFLUENCERS.value: {"confidence": 0.0},
            ActionType.MEDIA_CAMPAIGN.value: {"confidence": 0.0},
            ActionType.ORGANIZE_MOVEMENT.value: {"confidence": -0.02},
            ActionType.NEGOTIATE.value: {"resource_1": -200, "resource_2": -100},
            ActionType.FILE_LEGAL_ACTION.value: {"resource_1": -400, "confidence": -0.02},
            ActionType.SPREAD_IDEOLOGY.value: {"resource_1": -500, "resource_2": -300},
            
            # Aggressive
            ActionType.ATTACK.value: {"confidence": -0.10, "gdp_growth": -0.02},
            ActionType.SABOTAGE.value: {"confidence": -0.05, "resource_1": -500, "resource_2": -500},
            ActionType.EXPLOIT_VULNERABILITY.value: {"confidence": -0.05},
            ActionType.LEAK_SECRETS.value: {"confidence": -0.08},
            ActionType.BETRAY.value: {"resource_1": -200, "resource_2": -200},
            ActionType.SEEK_REVENGE.value: {"resource_1": -300, "resource_2": -200},
            
            # Defensive
            ActionType.FORTIFY.value: {"resource_1": -1000},
            ActionType.BUILD_DEFENSES.value: {"resource_1": -1000, "resource_2": -500},
            
            # Intel
            ActionType.GATHER_INTEL.value: {"resource_1": -300, "resource_2": -100},
        }

    async def update(self, db: AsyncSession, project_id: UUID, actions: List[AgentAction],
                     structured_world: StructuredWorldState) -> Dict[str, Any]:
        """
        1. Deduct agent resource burn based on deterministic action mapping.
        2. Apply market effects from actions.
        3. Trigger supply shocks/jobs-replaced.
        4. Recalculate prices.
        
        Returns: Dict containing price changes and economy state dict.
        """
        economy = await self._get_or_create(db, project_id)

        # 1 & 2. Apply deterministic action costs
        for action in actions:
            # We only apply macro costs if the action was executed (even if it failed, it burned resources)
            if action.executed:
                self._apply_action_economics(action, economy)

        # 3. Trigger supply shocks and global cascades
        # Global cascade: resource_1 shortage -> resource_2 demand
        if economy.resource_1_supply < 50000:
            economy.resource_2_supply -= 1000  # strain cascades
            self._add_event(structured_world, "resource_shortage_warning", "{resource_1} shortage is spiking {resource_2} demand")

        # Social cascades
        if economy.displaced_units > 100000:
            unemployment_increase = (economy.displaced_units // 100000) * 0.02
            economy.public_unemployment = min(1.0, economy.public_unemployment + unemployment_increase)
            # Reset the counter slightly so we don't trigger every turn, or just track total
            # Actually, since it's an absolute threshold, if it's over 100k, we just increase it 
            # and let the engine handle it. But to avoid infinite increase, we cap it.
            
        # Natural resource recovery (minor regeneration per step)
        economy.resource_1_supply = min(100000.0, economy.resource_1_supply + 1000)
        economy.resource_2_supply = min(50000.0, economy.resource_2_supply + 500)
        economy.resource_3_supply = min(7000.0, economy.resource_3_supply + 50)
        
        # GDP Growth applies slowly
        economy.market_confidence = max(0.0, min(1.0, economy.market_confidence))
        
        # 4. Recalculate prices
        price_changes = self._recompute_prices(economy)

        await db.commit()
        return {
            "price_changes": price_changes,
            "economy": {
                "resource_1_supply": economy.resource_1_supply,
                "resource_2_supply": economy.resource_2_supply,
                "resource_3_supply": economy.resource_3_supply,
                "public_unemployment": economy.public_unemployment,
                "gdp_growth": economy.gdp_growth,
                "market_confidence": economy.market_confidence,
                "displaced_units": economy.displaced_units,
            }
        }

    def _apply_action_economics(self, action: AgentAction, economy: GlobalEconomyState):
        """Modify economy based on deterministic action mapping."""
        atype = action.action_type
        
        impacts = self.action_impacts.get(atype, {})
        
        # Apply deterministic impacts
        if "resource_1" in impacts:
            economy.resource_1_supply = max(0.0, economy.resource_1_supply + impacts["resource_1"])
        if "resource_2" in impacts:
            economy.resource_2_supply = max(0.0, economy.resource_2_supply + impacts["resource_2"])
        if "resource_3_supply" in impacts:
            economy.resource_3_supply = max(0.0, economy.resource_3_supply + impacts["resource_3_supply"])
        if "displaced_units" in impacts:
            economy.displaced_units += impacts["displaced_units"]
        if "confidence" in impacts:
            economy.market_confidence = max(0.0, min(1.0, economy.market_confidence + impacts["confidence"]))
        if "gdp_growth" in impacts:
            economy.gdp_growth += impacts["gdp_growth"]

    def _recompute_prices(self, economy: GlobalEconomyState) -> Dict[str, float]:
        """Return resource -> price multiplier for this step."""
        return {
            "resource_1": 1.0 / max(0.1, economy.resource_1_supply / 100000.0),
            "resource_2": 1.0 / max(0.1, economy.resource_2_supply / 50000.0),
            "resource_3": 1.0 / max(0.1, economy.resource_3_supply / 7000.0),
        }

    def _add_event(self, structured_world: StructuredWorldState, action: str, outcome: str):
        """Add an economic shock to the world events log."""
        structured_world.recent_events.append(
            WorldEventRecord(
                step=0, # The exact step will be managed by simulation_engine if needed, or 0 indicates system event
                actor="market",
                action=action,
                target="global",
                outcome=outcome,
                visibility=1.0
            )
        )

    async def _get_or_create(self, db: AsyncSession, project_id: UUID) -> GlobalEconomyState:
        result = await db.execute(select(GlobalEconomyState).where(GlobalEconomyState.project_id == project_id))
        state = result.scalar_one_or_none()
        if not state:
            state = GlobalEconomyState(project_id=project_id)
            db.add(state)
            await db.flush()
        return state
