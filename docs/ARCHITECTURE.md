# MapR1 Architecture

MapR1 is an AI-powered world simulation engine built primarily with Python, FastAPI, and a React frontend. The application simulates branching timelines, emergent behaviors, and complex relationships across hypothetical scenarios.

## High-Level System Design

### 1. The Core Application (`backend/core/`)
Manages configuration (`settings`), database sessions, and connections to external APIs (LLM providers).
- **Database (`SQLAlchemy` & `AsyncPG`)**: Manages the persistent world state, storing Projects, Timelines, Entities, and Events.
- **Vector Memory (`ChromaDB`)**: Embeds and stores unstructured memories and Agent Diaries, allowing agents to query context using Semantic Search.

### 2. The Seeder (`backend/seeder/`)
Translates user prompts into rich foundational states for the simulation.
- **Theme Generator & Compiler**: Uses LLMs to generate the core DNA of the world.
- **Scenario Seeder**: Creates initial entities, relationships, and tensions.
- **Seed Committer**: Ingests the generated scenario and commits it to the persistent relational database as a new Project.

### 3. The Simulation Engine (`backend/simulation/`)
The computational heart of MapR1. It processes actions and world events.
- **Semantic Action Router**: Automatically maps agent intents to specific system handlers by understanding the semantics of an action using pre-computed embeddings.
- **Consequence Engine**: Evaluates the second-order effects of events and updates entity relationships and world tension.

### 4. The Simulation Theater (`backend/theater/`)
Orchestrates the passage of time and broadcasts state changes to subscribers.
- **Event Loop**: Runs the simulation iteratively, stepping through time and prompting agents for decisions.
- **Pacing Modes**: Supports modes like `AUTO_UNIFORM` and `MANUAL` to control the speed of the simulation.
- **Story Compiler**: Compiles the step-by-step history and agent logs into human-readable narratives and chapters.

### 5. API Layer (`backend/api/`)
A suite of FastAPI REST endpoints that expose the world state to the frontend or external clients. This includes routers for `projects`, `scenarios`, `entities`, `timelines`, `worlds`, `memory`, `agents`, and the `theater`.

## Data Flow

1. **Initialization:** The user submits a prompt via CLI or API. The **Seeder** generates the initial models and writes them to the Postgres DB.
2. **Simulation:** The **Theater** is started. On each step, it identifies active entities and requests their actions via the **Agent Decision Engine**.
3. **Action Execution:** Actions are routed to the **Simulation Engine**, which updates the world state, triggers consequences, and updates relationships.
4. **Memory Storage:** Important actions, thoughts, and world events are embedded and stored in the **Memory System** (ChromaDB) for future context.
5. **Compilation:** Once the theater completes, the **Story Compiler** extracts narratives from the event timeline to produce `story.md` and detailed agent diaries.
