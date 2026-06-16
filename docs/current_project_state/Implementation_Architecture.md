# MapR1 Implementation & Architecture (Detailed)

This document breaks down the exact technical architecture, data flow, and functional logic of the MapR1 backend.

---

## 🧬 1. The Scenario Seeder Pipeline (`backend/seeder/`)

The Scenario Seeder is responsible for "Genesis." It translates a raw user prompt into a fully populated PostgreSQL database schema ready for simulation. It relies on a multi-pass OpenRouter LLM workflow:

1. **Pass 0: DNA Extraction** (`dna_extractor.py`) - Distills the prompt into core themes, key variables, and conflict vectors.
2. **Pass 1: World Fabrication** (`world_fabricator.py`) - Establishes the macro `GlobalEconomyState` (initial compute, energy, unemployment) and `PublicBeliefState`.
3. **Pass 2: Entity Generation** (`entity_generator.py`) - Creates the organizations/factions.
4. **Pass 3: Agent Casting** (`agent_caster.py`) - Instantiates the `Agent` models. Assigns distinct archetypes (hacker, ceo, spy) and baseline personalities.
5. **Pass 4: Goal Weaving** (`goal_weaver.py`) - Assigns nested goals to agents. Crucially, it intentionally creates zero-sum conflicts between specific agents.
6. **Pass 5: Tension Wiring** (`tension_wirer.py`) - Pre-populates the database with existing rivalries, alliances, and asymmetric "hidden facts" placed into agents' memory stores.

---

## 🧠 2. The Decision Engine (`backend/agents/decision_engine.py`)

When the simulation asks an agent to act, the `DecisionEngine` coordinates an intricate data-gathering process before querying the LLM.

### The Intelligence Phase vs. Execution Phase
1. **Knowledge Threshold:** Agents start with a `knowledge_score` for their goals. If the score is below `0.65` (the `KNOWLEDGE_THRESHOLD`), the engine forces the agent into the **Intelligence Phase**. The only actions available to them are variants of "gather intelligence" or "observe".
2. **Phase Shift:** Once intelligence is gathered, the engine filters out "gather" actions and unlocks **Execution Actions** (e.g., `expand business`, `sabotage`, `propose policy`), prompting the LLM to make a decisive move based on what it learned.

### Prompt Construction
The prompt sent to the LLM is constructed by aggregating:
- **Memory Context:** Semantic retrieval of the top 3 recent, important, and similar memories via ChromaDB.
- **Mutable Psychology:** Current variables for `fear`, `paranoia`, `desperation`, etc.
- **Relationship Matrix:** Who they trust, who they hate, and pending alliance proposals.
- **Resource Scarcity:** Their current fractional share of global resources.

The LLM is required to output a strictly validated `AgentDecision` Pydantic model containing the chosen `action_type`, `reasoning`, `confidence`, and `affected_agents`.

---

## ⚙️ 3. The Simulation Loop (`backend/simulation/simulation_engine.py`)

The `SimulationEngine` runs the `simulate_step()` loop, orchestrating time and resolving actions asynchronously. The step follows a strict order of operations:

1. **Fire Delayed Events:** The system queries `scheduled_events` for any actions meant to resolve on the current step and applies their impacts to the world state.
2. **Roll Black Swans:** A low-probability RNG check determines if a global disruption alters the state before agents act.
3. **Agent Loop (Parallelizable):**
   - Each agent receives their restricted `_describe_situation()` (filtered by Fog of War).
   - The agent evaluates incoming proposals (alliances) and decides on an action.
   - The `ScarcityEngine` checks if the agent can "afford" the action. If blocked, the action automatically fails.
   - The action's success probability is calculated using the LLM's confidence, agent rationality/ambition, and scarcity penalties. A random roll determines execution success.
4. **Action Execution & Consequence:** The `ActionExecutorV2` modifies local state, while the `ConsequenceEngine` determines cascading relational effects (e.g., failed sabotage creates a permanent rivalry).
5. **System Updates:**
   - **Economy:** The `EconomySystem` deducts the hard-coded costs of actions (e.g., `EXPAND_BUSINESS` costs 2000 compute) and checks for global shortages.
   - **Psychology:** Agent traits are mutated based on the step's trauma or success.
6. **Pattern Detection:** An LLM analyzes the entire step's log to identify high-level emergent trends (e.g., "The tech sector is forming an oligopoly to hoard compute").

---

## 🗄️ Database Architecture Highlights
- **`GlobalEconomyState`**: Holds global metrics. Contains a JSONB `agent_holdings` column for high-speed resource manipulation.
- **`AgentMemory`**: Indexed by agent ID and memory type, linked to vector embeddings for similarity search.
- **`ScheduledEvent`**: The foundation of the Delayed Effects system, containing a `trigger_turn` and an `impact_data` payload.
