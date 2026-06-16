# MapR1 Emergent Systems Guide (Detailed)

MapR1 abandons scripted narratives in favor of systemic emergence. The `backend/systems/` directory contains 8 interconnected systems that act as the "physics" of the simulation. Here is exactly how they are implemented in the code.

---

## 1. Global Economy (`economy_system.py`)
**Concept**: Growth has hard costs.
**Implementation**: 
- The system maps deterministic costs to specific `ActionType` enums. For example:
  - `EXPAND_BUSINESS` → deducts 2000 compute, adds 50,000 to `ai_jobs_replaced`, boosts market confidence by +0.01.
  - `RESEARCH` → deducts 3000 compute and 1000 energy.
  - `SABOTAGE` → deducts 500 compute and 500 energy.
- **Global Cascades**: At the end of the step, the system checks macro limits. If `compute_supply` falls below 50,000, it triggers a severe cascade, actively draining `energy_supply` by 1000 (representing inefficient power usage) and spawning an `energy_shortage_warning` event.
- **Job Replacement:** If `ai_jobs_replaced` exceeds 100,000, it permanently pushes up `public_unemployment` by 2%.

## 2. Resource Scarcity (`scarcity_system.py`)
**Concept**: Agents cannot execute actions they cannot afford.
**Implementation**:
- Hooked into the simulation loop *before* an action executes.
- It compares the action's cost from the Economy mapping against the agent's fractional resource share in the `StructuredWorldState`.
- If resources are highly strained, it applies a `success_penalty` (reducing the LLM's confidence probability). If resources are completely depleted, it returns a "Hard Block," aborting the action entirely.

## 3. Fog of War (`fog_system.py`)
**Concept**: The death of omniscience.
**Implementation**: 
- Replaces global event broadcasting. Agents no longer receive a global `recent_events` log in their prompt.
- When an action executes, the system evaluates `base_visibility` vs. the actor's `exposure`. It writes a `FactRecord` (containing a `confidence` float) directly into observing agents' `AgentBeliefState.known_facts` JSONB dictionary.
- Agents act purely on these partial, sometimes incorrect, localized beliefs.

## 4. Trust & Misinformation (`trust_system.py`)
**Concept**: Reality is shaped by perceived belief.
**Implementation**: 
- Maintains a `PublicBeliefState` mapping topics to a confidence score (0.0 to 1.0).
- Agents possess a `propaganda_power` and `credibility` stat. When they execute a `media_campaign`, the delta shift in public belief is multiplied by their propaganda power and dampened by public `paranoia`.
- Agents can learn facts with "noise" applied to the true confidence, allowing for organic misunderstandings in the simulation.

## 5. Psychological Evolution (`psychology_system.py`)
**Concept**: Agents suffer trauma and adapt.
**Implementation**: 
- Modifies a Pydantic `MutablePsychology` object tracking 0.0-1.0 stats (fear, paranoia, greed, ego, desperation, radicalization).
- **Failure Mechanics**: If an action fails, `consecutive_failures` increments. `fear` increases by 0.1, `paranoia` by 0.08. If `consecutive_failures >= 3`, the agent suffers a radicalization spike (+0.3) and extreme paranoia (+0.2).
- **Resource Trauma**: If an agent's resource share drops below 30%, `greed` (+0.15) and `desperation` (+0.2) spike drastically.
- **Betrayal**: Being involved in betrayal drops `idealism` by 0.2 and spikes `risk_tolerance` and `paranoia`.

## 6. Delayed Effects & Time Bombs (`delayed_effect_system.py`)
**Concept**: Consequences have lag.
**Implementation**:
- Exposes a `schedule()` function that writes a `ScheduledEvent` row to the database with a `trigger_turn` integer (e.g., `current_step + 4`) and a JSONB `impact_data` payload.
- In `simulate_step()`, the engine queries the database for all events where `trigger_turn <= current_step` and `is_fired == False`.
- These payloads immediately mutate the world state before agents even make their decisions for the turn, creating sudden, unexpected crises.

## 7. Black Swan Events (`black_swan_system.py`)
**Concept**: The universe is chaotic.
**Implementation**:
- Contains an array of highly disruptive payloads, such as "Massive Solar Storm" (0.05% chance) or "AI Generated Religion Emerges" (0.5% chance).
- `roll()` is called at the very beginning of the simulation step.
- If triggered, the payload overrides standard market conditions (e.g., Solar Storm instantly crashes Tech and Energy by -0.8).

## 8. Nonlinear Public Opinion (`public_opinion_system.py`)
**Concept**: Society ignores issues until a breaking point is reached.
**Implementation**:
- Tracks sentiment on a 0.0 to 1.0 scale, mapped to thresholds: `stable` (0.0), `concerned` (0.3), `fearful` (0.5), `angry` (0.7), `radicalized` (0.85), `revolutionary` (0.95).
- Employs a non-linear velocity formula: `new = current + delta * (1.0 + abs(current - 0.5))`.
- **The Result:** When public opinion passes 0.5, the velocity of change accelerates dramatically. A small incident can instantly tip a "fearful" populace into a "revolutionary" one.
