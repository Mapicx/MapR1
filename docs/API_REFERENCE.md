# MapR1 API Reference

The MapR1 backend is built on FastAPI and exposes a comprehensive REST API to interact with the simulated worlds and agents. When the server is running, the interactive Swagger UI is available at `/docs` (e.g., `http://localhost:8000/docs`).

Below is an overview of the core API routers and their general purposes:

## 1. Health (`/health`)
- Used to verify that the API server is up and responding.
- Used to verify database connections and LLM availability.

## 2. Projects (`/api/projects`)
- Projects represent a complete simulated world or a specific seeded scenario.
- Endpoints allow you to fetch all projects, get project details, or delete old simulation worlds.

## 3. Scenarios (`/api/scenarios`)
- Primarily used during the Scenario Seeding phase.
- Endpoints accept a prompt and trigger the LLM to generate the foundational models for a new scenario before committing it as a project.

## 4. Entities & Agents (`/api/entities` & `/api/agents`)
- Entities represent both individuals (agents) and abstract constructs (factions, corporations).
- Endpoints retrieve an entity's current state, their ongoing goals, their inventory, and their status within the simulation.
- Agent-specific endpoints may expose agent diaries or thoughts for debugging and frontend visualization.

## 5. Worlds & Timelines (`/api/worlds` & `/api/timelines`)
- Timelines trace the sequential progress of a simulation (steps).
- Endpoints fetch the current step, the state of the world, and query historical events that have transpired in the timeline.

## 6. Memory (`/api/memory`)
- Interacts with the Vector Memory store (ChromaDB).
- Allows querying an agent's memory for specific contexts or concepts using semantic search.

## 7. Simulation & Theater (`/api/simulation` & `/theater`)
- The Theater endpoints orchestrate the simulation loop.
- Features controls to start, pause, or step through the simulation.
- Exposes WebSocket connections to stream real-time events, agent actions, tension updates, and narrative progression directly to the frontend.
