# Comprehensive Action-Consequence Audit

This report audits all actions currently supported by the MapR1 simulation engine, detailing their consequences (success, failure, partial, delayed) across world state, psychology, relationships, and memory. It identifies gaps, repetitive templates, and missing contextualizations.

---

## 1. Action Consequence Matrix

### Alliance & Relationship Management
| Action | Success Consequences | Failure Consequences | Missing / Gaps | Contextualized? |
|--------|----------------------|----------------------|----------------|-----------------|
| `execute_alliance` | Adds proposal to `pending_proposals`. No immediate world state or relationship change. | Influence -0.05 if no target. | Success lacks immediate relationship warmth or memory logging. | No |
| `execute_build_relationship` | Adds proposal to `pending_proposals`. | No target found (No impact). | Same as alliance; no actual trust/strength mutation on initiation. | No |

### Subterfuge & Covert Ops
| Action | Success Consequences | Failure Consequences | Missing / Gaps | Contextualized? |
|--------|----------------------|----------------------|----------------|-----------------|
| `execute_sabotage` | Target resources -0.2, reputation -0.15. Low visibility event. | **Contextual Consequence Engine** (Retaliation, exposure, paranoia, resource drain). | Success is purely static; no contextual damage scaling. | **Yes** (Failure) |
| `execute_exploit_vulnerability` | Target resources -0.25, power -0.2. Low visibility. | *None.* Just returns success=False. | Complete lack of failure consequences (no exposure risk). | No |
| `execute_leak_secrets` | Spread belief via `TrustMisinformationSystem` covertly. | **Contextual Consequence Engine** (Misinformation spiral, source discovery, panic). | Success is good, uses secondary system. | **Yes** (Failure) |
| `execute_betrayal` | Massive trust/strength drop, alliances broken, target resources -0.25, actor power +0.15, rivalry created, severe memory and psychology (paranoia) mutations. | **Contextual Consequence Engine** (Blackmail, isolation, secret exposure, faction fracture). | Fully fleshed out. | **Yes** (Failure) |
| `execute_gather_intel` | Never fails. Uncovers facts, stores in `AgentMemoryManager` and `FogOfWarSystem`, updates goal knowledge. | N/A | Acts as an internal mechanic rather than a risky action. | N/A |

### Conflict & Aggression
| Action | Success Consequences | Failure Consequences | Missing / Gaps | Contextualized? |
|--------|----------------------|----------------------|----------------|-----------------|
| `execute_attack` | Target resources -0.25, power -0.20. Actor power +0.10. Trust -0.8. Rivalry created/intensified. | Actor power -0.15, exposure +0.3. | Failure is totally static. Needs contextual retaliation. | No |
| `execute_hostile_takeover` | Target resources -0.4. Actor gains 80% of target resources, actor power +0.2. | Actor resources -0.3. | Failure is a static penalty. High stakes, deserves contextual failure. | No |

### Politics & Public Influence
| Action | Success Consequences | Failure Consequences | Missing / Gaps | Contextualized? |
|--------|----------------------|----------------------|----------------|-----------------|
| `execute_campaign` | Public opinion +0.25 (nonlinear). Media attention +0.3, regulatory pressure +0.2. Actor rep +0.15. | Actor resources -0.05. | Failure is completely ignored by the public (static). | No |
| `execute_policy` | Regulatory pressure +0.3, actor power +0.2. | **Contextual Consequence Engine** (Backlash, deadlock, activist mobilization). | Fully fleshed out on failure. | **Yes** (Failure) |
| `execute_lobbying` | Target power -0.15, actor power +0.15. | Actor exposure +0.3, target trust -0.8 (caught). | Static failure penalty. | No |
| `execute_media_campaign`| Target rep -0.25, spreads misinformation/belief. | Actor rep -0.15. | Static failure penalty. | No |
| `execute_legal_action` | Target resources -0.2. | Actor resources -0.15, reputation -0.1. | Static failure penalty. | No |

### Economy, Expansion & Talent
| Action | Success Consequences | Failure Consequences | Missing / Gaps | Contextualized? |
|--------|----------------------|----------------------|----------------|-----------------|
| `execute_expansion` | Actor resources +0.15, power +0.1. Market conditions +0.05. | Actor resources -0.10. | Highly generic. Could use scarcity context. | No |
| `execute_acquisition` | Target power x0.4. Actor gains 50% target resources, power +0.2. | Actor resources -0.15, regulatory pressure +0.3. | Target is effectively deleted/absorbed, but failure is static. | No |
| `execute_negotiation` | Mutual resource gain (+0.1, +0.08). Trust +0.15, strength +0.20. | Actor reputation -0.05. | Missing actual trade context. Generic failure. | No |
| `execute_investment` | Actor resources -0.05, power +0.15. | Actor resources -0.10. | Generic static outcome. | No |
| `execute_contract_bid`| Actor resources +0.3, power +0.15. | Actor resources -0.1. | Generic static outcome. | No |
| `execute_defensive_restructuring` | Exposure -> 0.0, resources -0.15. | Resources -0.15. | Success magically erases all exposure without context limits. | No |
| `execute_talent` | Target power -0.1, Actor +0.12. Rivalry created. Trust -0.4. | Actor rep -0.1, rivalry created. | Duplicate of `poach_talent`. Static failure. | No |
| `execute_poach_talent`| Target power -0.1, Actor +0.1. | Target trust -0.5. | Duplicate of `execute_talent`. | No |

### Generic
| Action | Success Consequences | Failure Consequences | Missing / Gaps | Contextualized? |
|--------|----------------------|----------------------|----------------|-----------------|
| `execute_generic` | Actor resources +0.08. | Actor resources -0.05. | Highly repetitive generic outcome for unknown actions. | No |

---

## 2. Gaps & Repetitive Patterns

1. **Static Failures:** The vast majority of actions (except Sabotage, Policy, Leak, and Betrayal) have completely static failure consequences. For example, failing an `attack` ALWAYS results in `-0.15 power` and `+0.3 exposure`.
2. **Missing Exposure Risks:** `execute_exploit_vulnerability` has literally zero consequences upon failure (`impact={}`). The agent risks absolutely nothing by attempting it.
3. **Redundant Actions:** `execute_talent` and `execute_poach_talent` both exist, do almost exactly the same thing, but mutate state slightly differently (e.g., one creates a rivalry, the other just drops trust). 
4. **No Psychological Mutations on Most Actions:** Besides `betrayal` and the new contextual failures, actions do not mutate agent psychology (fear, paranoia, ego, desperation) even when they succeed or fail massively (e.g., winning a `hostile_takeover` should boost ego).
5. **Success is Too Deterministic:** Success consequences are rigidly static. A successful sabotage always drops target resources by exactly 20%, regardless of whether it's against a massive corporation or a struggling startup, or what the scarcity state is.

## 3. Prioritized Recommendations

### Priority 1: Contextualize High-Stakes Failures
The following actions represent massive escalations and their failures should trigger the `ContextualConsequenceEngine`:
1. `execute_attack`: A failed attack should lead to retaliation, alliances stepping in, or public condemnation depending on context.
2. `execute_hostile_takeover`: Failing a takeover should cause market panics, regulatory lockouts, or extreme resource burns.
3. `execute_media_campaign` / `execute_campaign`: Failing to control the narrative should contextualize into public backlash, censorship, or apathy based on public fear and visibility.

### Priority 2: Fix Broken/Redundant Actions
1. Remove `execute_poach_talent` and consolidate its logic entirely into `execute_talent`.
2. Add exposure and resource penalties to `execute_exploit_vulnerability` failure so it isn't a "free roll".
3. Add memory logging to `execute_alliance` so agents remember who proposed an alliance (even while it is pending).

### Priority 3: Contextualize Successes
Create a `resolve_success()` path in the `ContextualConsequenceEngine` to make successful outcomes dynamic. For example:
- **Sabotage Success:** If target paranoia is low and visibility is low, it's an "unexplained accident." If target paranoia is high, they immediately assume foul play even if they don't know who did it.
- **Attack Success:** If target is an ally of a powerful faction, success triggers delayed retaliation from the ally.

### Priority 4: Psychology Integration
Currently, most world state changes update `agent_power`, `agent_resources`, and `agent_reputation`. We need `execute_attack`, `execute_acquisition`, and `execute_legal_action` to directly mutate `ego`, `fear`, and `desperation`. Winning a lawsuit should boost ego; getting attacked should spike fear and desperation.
