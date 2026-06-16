"""
MapR1 — Semantic Action Router

Replaces brittle keyword matching with embedding-based semantic routing.

How it works:
  1. At startup, embed a rich description for each handler (once, cached in RAM)
  2. When the LLM returns an action string, embed it locally (~3ms on GPU)
  3. Cosine similarity against the cached handler embeddings → pick best match
  4. Fall back to _execute_generic only if similarity < threshold

Uses sentence-transformers (all-MiniLM-L6-v2) which is already in pyproject.toml.
Runs on CUDA if available, CPU otherwise — both are fast for 15-vector lookup.
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Dict, List, Optional, Tuple
from loguru import logger


# ── Handler registry ──────────────────────────────────────────────────────────
# Each entry maps a handler name to a list of natural-language descriptions
# that capture what that handler does. Multiple descriptions improve recall.

HANDLER_DESCRIPTIONS: Dict[str, List[str]] = {
    "gather_information": [
        "gather information and intelligence about the situation",
        "collect data, research, investigate, learn about competitors",
        "gather intelligence, spy, surveil, observe and collect facts",
    ],
    "expansion": [
        "expand business operations, grow the company, scale up",
        "expand territory, increase market presence, grow operations",
        "open new offices, enter new markets, scale the business",
    ],
    "product_launch": [
        "launch a new product or service to the market",
        "release a product, ship a feature, introduce a new offering",
        "product launch, go to market, release new software or hardware",
    ],
    "acquisition": [
        "acquire a company, buy out a competitor, hostile takeover",
        "merge with or purchase another organization",
        "acquisition, buyout, takeover, purchase a rival company or asset",
        "launch hostile acquisition, acquire NovaTech, buy competitor",
    ],
    "alliance": [
        "form a strategic alliance, partnership, or coalition",
        "partner with another organization, build a joint venture",
        "create alliance, form partnership, cooperate with another party",
        "partner with Greenpeace, join coalition, form strategic partnership",
    ],
    "attack": [
        "attack, assault, or aggressively undermine a competitor or enemy",
        "launch an offensive, strike against an opponent",
        "competitive attack, hostile action, aggressive move against rival",
    ],
    "negotiation": [
        "negotiate a deal, treaty, or agreement with another party",
        "diplomatic negotiation, mediate, broker a deal",
        "negotiate terms, reach agreement, settle dispute diplomatically",
        "brief city council members, lobby officials, negotiate with stakeholders",
    ],
    "investment": [
        "invest in research and development, fund innovation",
        "allocate capital to R&D, invest in technology or infrastructure",
        "invest resources, fund a project, back a new initiative",
    ],
    "policy": [
        "propose or implement a new policy, regulation, or law",
        "file a formal complaint, regulatory action, legal filing",
        "policy change, regulatory proposal, file complaint with regulator",
        "file formal complaint with environmental regulator, legal action",
    ],
    "sabotage": [
        "sabotage, infiltrate, or covertly undermine an opponent",
        "covert operation, espionage, disrupt competitor operations",
        "exploit a vulnerability, hack, sabotage supply chain or systems",
        "exploit competitor supply chain weakness, exploit security flaw",
    ],
    "campaign": [
        "run a public campaign, spread awareness, organize activism",
        "media campaign, expose wrongdoing to the press, whistleblowing",
        "organize protest, create viral campaign, spread awareness publicly",
        "expose environmental violations to media, brief journalist, public pressure",
        "connect whistleblower with journalist, amplify activist platform",
    ],
    "relationship_building": [
        "build relationships, network, make connections with allies",
        "help others, support allies, build goodwill and trust",
        "build grassroots movement, recruit supporters, form community",
        "partner with Greenpeace, coordinate with activist coalition",
    ],
    "observe": [
        "observe and wait, monitor the situation, take no action",
        "watch and learn, stay passive, gather passive intelligence",
    ],
    "talent": [
        "hire key talent, recruit employees, poach engineers or executives",
        "headhunt, recruit staff, build the team, hire away from competitor",
        "poach competitor engineers, hire key talent, recruit executives",
    ],
    "financial": [
        "optimize financial operations, manage cash flow, cut costs",
        "secure funding, raise capital, manage budget, reduce expenses",
        "financial optimization, cost cutting, fundraising, cash management",
    ],
}


class SemanticActionRouter:
    """
    Routes LLM action strings to executor handler names using embeddings.
    Initialized once at startup; subsequent lookups are ~3ms on GPU.
    """

    SIMILARITY_THRESHOLD = 0.30  # below this → generic handler

    def __init__(self):
        self._model = None
        self._handler_names: List[str] = []
        self._handler_matrix: Optional[np.ndarray] = None  # shape (N_descriptions, 384)
        self._description_to_handler: List[str] = []       # parallel list
        self._ready = False

    def initialize(self) -> None:
        """
        Load the embedding model and pre-embed all handler descriptions.
        Call once at application startup (inside asyncio startup event is fine —
        sentence-transformers encode() is synchronous but fast).
        """
        try:
            from sentence_transformers import SentenceTransformer
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"SemanticActionRouter: loading model on {device}")

            self._model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

            # Flatten all descriptions, keeping track of which handler they belong to
            all_descriptions: List[str] = []
            self._description_to_handler = []

            for handler_name, descriptions in HANDLER_DESCRIPTIONS.items():
                for desc in descriptions:
                    all_descriptions.append(desc)
                    self._description_to_handler.append(handler_name)

            # Embed all descriptions in one batch (fast)
            embeddings = self._model.encode(
                all_descriptions,
                batch_size=64,
                normalize_embeddings=True,  # unit vectors → dot product = cosine sim
                show_progress_bar=False,
            )
            self._handler_matrix = np.array(embeddings, dtype=np.float32)

            self._ready = True
            logger.success(
                f"SemanticActionRouter ready: {len(all_descriptions)} descriptions "
                f"across {len(HANDLER_DESCRIPTIONS)} handlers on {device}"
            )

        except Exception as e:
            logger.error(f"SemanticActionRouter failed to initialize: {e}")
            logger.warning("Falling back to keyword routing")
            self._ready = False

    def route(self, action_string: str) -> Tuple[str, float]:
        """
        Find the best handler for an action string.

        Returns:
            (handler_name, similarity_score)
            handler_name is one of the keys in HANDLER_DESCRIPTIONS,
            or "generic" if similarity < threshold or model not ready.
        """
        if not self._ready or self._model is None:
            return self._keyword_fallback(action_string), 0.0

        try:
            # Embed the action string (~3ms on GPU)
            query_vec = self._model.encode(
                [action_string],
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0].astype(np.float32)

            # Cosine similarity against all handler descriptions
            similarities = self._handler_matrix @ query_vec  # shape (N,)

            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])
            best_handler = self._description_to_handler[best_idx]

            logger.debug(
                f"Routed '{action_string[:60]}' -> {best_handler} "
                f"(similarity: {best_score:.3f})"
            )

            if best_score < self.SIMILARITY_THRESHOLD:
                logger.debug(f"Score below threshold, using generic handler")
                return "generic", best_score

            return best_handler, best_score

        except Exception as e:
            logger.error(f"Semantic routing failed: {e}")
            return self._keyword_fallback(action_string), 0.0

    def _keyword_fallback(self, action: str) -> str:
        """Simple keyword fallback if model isn't loaded."""
        a = action.lower()
        if "gather" in a and ("info" in a or "intel" in a):
            return "gather_information"
        if "expand" in a or "grow" in a:
            return "expansion"
        if "acqui" in a or "takeover" in a or "buyout" in a:
            return "acquisition"
        if "launch" in a and ("product" in a or "service" in a or "feature" in a):
            return "product_launch"
        if "alliance" in a or "coalition" in a:
            return "alliance"
        if "attack" in a or "assault" in a:
            return "attack"
        if "negotiat" in a or "treaty" in a or "deal" in a:
            return "negotiation"
        if "invest" in a or "r&d" in a or "fund" in a:
            return "investment"
        if "policy" in a or "regulat" in a or "complaint" in a or "file" in a:
            return "policy"
        if "sabotage" in a or "infiltrat" in a or "exploit" in a:
            return "sabotage"
        if "campaign" in a or "expose" in a or "media" in a or "protest" in a:
            return "campaign"
        if "hire" in a or "recruit" in a or "poach" in a or "talent" in a:
            return "talent"
        if "observe" in a or "wait" in a:
            return "observe"
        if "help" in a or "support" in a or "build relation" in a:
            return "relationship_building"
        return "generic"

    @property
    def is_ready(self) -> bool:
        return self._ready


# Module-level singleton — initialized once at startup
action_router = SemanticActionRouter()
