"""
MapR1 — Simulation Logger

Writes structured, human-readable logs for every simulation run.
Each run gets its own folder under logs/simulations/<project_id>/<timestamp>/

Files written per run:
  - simulation.log      → full chronological log (text)
  - decisions.jsonl     → one JSON object per agent decision
  - actions.jsonl       → one JSON object per executed action
  - patterns.jsonl      → one JSON object per detected pattern
  - summary.json        → final summary written at end of run
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger


class SimulationLogger:
    """
    Structured logger for a single simulation run.
    Instantiate once per project and reuse across steps.
    """

    def __init__(self, project_id: UUID, run_label: Optional[str] = None):
        self.project_id = str(project_id)
        self.run_label = run_label or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.utcnow()

        # Build output directory
        self.run_dir = (
            Path("logs") / "simulations" / self.project_id / self.run_label
        )
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Open file handles
        self._log_file = open(self.run_dir / "simulation.log", "a", encoding="utf-8")
        self._decisions_file = open(self.run_dir / "decisions.jsonl", "a", encoding="utf-8")
        self._actions_file = open(self.run_dir / "actions.jsonl", "a", encoding="utf-8")
        self._patterns_file = open(self.run_dir / "patterns.jsonl", "a", encoding="utf-8")

        # Stats
        self.step_count = 0
        self.total_actions = 0
        self.total_patterns = 0

        self._write_log(f"{'='*60}")
        self._write_log(f"SIMULATION RUN STARTED")
        self._write_log(f"Project : {self.project_id}")
        self._write_log(f"Run     : {self.run_label}")
        self._write_log(f"Time    : {self.start_time.isoformat()}")
        self._write_log(f"{'='*60}\n")

        logger.info(f"SimulationLogger writing to {self.run_dir}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _write_log(self, text: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        self._log_file.write(line)
        self._log_file.flush()

    def _write_jsonl(self, fh, record: Dict[str, Any]):
        fh.write(json.dumps(record, default=str) + "\n")
        fh.flush()

    # ── Public API ────────────────────────────────────────────────────────────

    def log_step_start(self, step: int, agent_count: int):
        self.step_count = step
        self._write_log(f"\n{'─'*50}")
        self._write_log(f"STEP {step} — {agent_count} agents acting")
        self._write_log(f"{'─'*50}")

    def log_step_end(self, step: int, action_count: int, pattern_count: int):
        self._write_log(
            f"STEP {step} COMPLETE — {action_count} actions, {pattern_count} patterns detected\n"
        )

    def log_decision(
        self,
        step: int,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        agent_role: str,
        action: str,
        reasoning: str,
        confidence: float,
        expected_outcome: str,
        risks: List[str],
        affected_agents: List[str],
    ):
        """Log an agent's LLM decision before execution."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "step": step,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "agent_role": agent_role,
            "action": action,
            "reasoning": reasoning,
            "confidence": confidence,
            "expected_outcome": expected_outcome,
            "risks": risks,
            "affected_agents": affected_agents,
        }
        self._write_jsonl(self._decisions_file, record)

        # Human-readable block in simulation.log
        self._write_log(f"  DECISION  [{agent_name} / {agent_type}]")
        self._write_log(f"    Action    : {action}")
        self._write_log(f"    Confidence: {confidence:.0%}")
        self._write_log(f"    Reasoning : {reasoning}")
        self._write_log(f"    Expected  : {expected_outcome}")
        if risks:
            self._write_log(f"    Risks     : {', '.join(risks)}")
        if affected_agents:
            self._write_log(f"    Affects   : {', '.join(affected_agents)}")

    def log_action(
        self,
        step: int,
        agent_id: str,
        agent_name: str,
        action_type: str,
        success: bool,
        outcome: str,
        impact: Dict[str, Any],
        side_effects: List[str],
    ):
        """Log the result of executing an action."""
        self.total_actions += 1
        record = {
            "ts": datetime.utcnow().isoformat(),
            "step": step,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "action_type": action_type,
            "success": success,
            "outcome": outcome,
            "impact": impact,
            "side_effects": side_effects,
        }
        self._write_jsonl(self._actions_file, record)

        status = "✓ SUCCESS" if success else "✗ FAILED "
        self._write_log(f"  ACTION    [{status}] {agent_name} → {action_type}")
        self._write_log(f"    Outcome : {outcome}")
        if impact:
            impact_str = ", ".join(f"{k}: {v:+.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in impact.items())
            self._write_log(f"    Impact  : {impact_str}")
        if side_effects:
            self._write_log(f"    Effects : {', '.join(side_effects)}")

    def log_pattern(
        self,
        step: int,
        pattern_id: str,
        pattern_type: str,
        title: str,
        description: str,
        significance: float,
        involved_agents: List[str],
        evidence: List[str],
        predictions: List[str],
    ):
        """Log a detected emergent pattern."""
        self.total_patterns += 1
        record = {
            "ts": datetime.utcnow().isoformat(),
            "step": step,
            "pattern_id": pattern_id,
            "pattern_type": pattern_type,
            "title": title,
            "description": description,
            "significance": significance,
            "involved_agents": involved_agents,
            "evidence": evidence,
            "predictions": predictions,
        }
        self._write_jsonl(self._patterns_file, record)

        self._write_log(f"\n  ★ PATTERN DETECTED: {title}")
        self._write_log(f"    Type        : {pattern_type}")
        self._write_log(f"    Significance: {significance:.0%}")
        self._write_log(f"    Description : {description}")
        if involved_agents:
            self._write_log(f"    Agents      : {', '.join(involved_agents)}")
        if evidence:
            for ev in evidence[:3]:
                self._write_log(f"    Evidence    : {ev}")
        if predictions:
            for pred in predictions[:2]:
                self._write_log(f"    Prediction  : {pred}")

    def log_world_state(self, step: int, state: Dict[str, Any]):
        """Log a snapshot of the world state."""
        self._write_log(f"\n  WORLD STATE (step {step}):")
        for k, v in list(state.items())[:20]:
            self._write_log(f"    {k}: {v}")

    def log_error(self, context: str, error: str):
        self._write_log(f"  !! ERROR [{context}]: {error}")

    def finalize(self, agents: List[Dict], extra: Optional[Dict] = None):
        """Write summary.json and close all file handles."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        summary = {
            "project_id": self.project_id,
            "run_label": self.run_label,
            "started_at": self.start_time.isoformat(),
            "ended_at": end_time.isoformat(),
            "duration_seconds": duration,
            "steps_completed": self.step_count,
            "total_actions": self.total_actions,
            "total_patterns": self.total_patterns,
            "agents": agents,
            **(extra or {}),
        }

        summary_path = self.run_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        self._write_log(f"\n{'='*60}")
        self._write_log(f"SIMULATION RUN COMPLETE")
        self._write_log(f"Duration : {duration:.1f}s")
        self._write_log(f"Steps    : {self.step_count}")
        self._write_log(f"Actions  : {self.total_actions}")
        self._write_log(f"Patterns : {self.total_patterns}")
        self._write_log(f"Logs     : {self.run_dir}")
        self._write_log(f"{'='*60}")

        self._log_file.close()
        self._decisions_file.close()
        self._actions_file.close()
        self._patterns_file.close()

        logger.success(f"Simulation logs saved to {self.run_dir}")
        return str(self.run_dir)


# ── Registry: one logger per active project ───────────────────────────────────

_active_loggers: Dict[str, SimulationLogger] = {}


def get_sim_logger(project_id: UUID, run_label: Optional[str] = None) -> SimulationLogger:
    """Get or create a SimulationLogger for a project."""
    key = str(project_id)
    if key not in _active_loggers:
        _active_loggers[key] = SimulationLogger(project_id, run_label)
    return _active_loggers[key]


def close_sim_logger(project_id: UUID, agents: List[Dict], extra: Optional[Dict] = None) -> str:
    """Finalize and remove the logger for a project. Returns log directory path."""
    key = str(project_id)
    sim_logger = _active_loggers.pop(key, None)
    if sim_logger:
        return sim_logger.finalize(agents, extra)
    return ""
