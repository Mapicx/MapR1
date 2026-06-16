# MapR1 - AI Imagination Engine (Detailed Overview)

> **MapR1 is a computational imagination system designed to simulate hypothetical scenarios, explore second-order consequences, and model emergent multi-agent behavior within persistent realities.**

---

## 🎯 The Core Philosophy: Moving Beyond Chatbots

Standard LLMs act as omniscient oracles: you ask a question, and they provide an answer based on statistical likelihood. MapR1 shifts the paradigm from "What is the answer?" to **"What could happen?"**

It achieves this by removing omniscience from the LLM. Instead of asking an LLM to generate a story, MapR1 spawns multiple autonomous **Agents** inside a structured database. The LLM is used as the "brain" for these agents, but the world's physics—economics, physics, public opinion, and trust—are strictly governed by hard-coded, deterministic backend systems. 

This forces the LLM to navigate a restrictive, high-stakes environment, resulting in unscripted, emergent narratives.

---

## 🧩 Deep Dive: Core Features

### 1. The Scenario Seeder (World Genesis)
Instead of starting with a blank slate, the engine uses a 6-pass pipeline to construct a deep, dramatically viable world state from a single prompt (e.g., *"What if AGI is achieved by 2029?"*).
- **Entities & Factions:** The engine creates corporations, rogue states, or activist groups.
- **Dramatic Casting:** Agents aren't just random NPCs. They are cast into dramatic roles (Protagonist, Antagonist, Catalyst, Wildcard) to ensure natural tension.
- **Goal Weaving:** Goals are designed to conflict. If Agent A's goal is to open-source AGI, Agent B's goal will naturally involve securing a monopoly over it.

### 2. Autonomous, Non-Omniscient Agents
Agents in MapR1 are highly complex state machines driven by LLM reasoning:
- **Fog of War:** Agents do not know the global state. They only know their `known_facts` and `beliefs`. They can be lied to, manipulated, or act on outdated intelligence.
- **Mutable Psychology:** An agent's personality isn't static. It tracks variables like `paranoia`, `desperation`, `fear`, and `radicalization`. A rational CEO might slowly devolve into a paranoid radical if their actions repeatedly fail or if they face resource starvation.
- **Memory Systems:** Agents use ChromaDB to store episodic memories. Before making a decision, they perform a semantic search to recall past betrayals, successes, or observations relevant to their current situation.

### 3. The Physics of Emergence
MapR1 relies on 8 interconnected backend systems that enforce the rules of reality:
- **Scarcity & Economics:** Agents compete for finite global pools of Compute, Energy, and Talent. Expansion costs resources. 
- **Consequences:** Actions have real weight. Sabotage carries the risk of exposure, which destroys reputation and forms rivalries.
- **Public Opinion:** Society tracks sentiment non-linearly. Tipping points in public anger can trigger regulatory crackdowns that instantly change the rules of the simulation.

---

## 🛠️ The Technology Stack

MapR1 is built for high-performance, asynchronous, and type-safe simulation:

- **Backend Framework:** FastAPI (Python 3.11+) handles the RESTful architecture and asynchronous simulation orchestration.
- **Database Layer:** Supabase PostgreSQL with `SQLAlchemy` async ORM. Complex states (like agent beliefs or market conditions) are stored efficiently in `JSONB` columns.
- **Vector Storage:** ChromaDB handles agent memory, converting text into vector embeddings using `sentence-transformers` for semantic retrieval.
- **AI/LLM Engine:** 
  - **Local Processing:** Ollama running models like Qwen 3.5:4b handles agent decision-making.
  - **Structured Output:** The engine strictly enforces JSON schemas using **Instructor** and **Pydantic**. This means the LLM never outputs plain text; it outputs validated Python objects (e.g., `AgentDecision(action="sabotage", confidence=0.8, target="agent_b")`), eliminating parsing errors.
- **Frontend Visualization (In Progress):** A React + Three.js interface that visualizes the simulation as a 3D universe, with scenarios as planets and agents as orbiting satellites connected by relationship and action beams.
