# MapR1 Frontend Overview

The MapR1 frontend allows users to visualize simulated worlds, interact with autonomous agents, and track the flow of events across branching timelines.

## Structure and Technologies
The main frontend application is located in `frontend/mapr1-app/`.
- **Framework:** React 18+ with [Vite](https://vitejs.dev/) for fast bundling and hot module replacement.
- **Styling:** [Tailwind CSS](https://tailwindcss.com/) for utility-first styling and rapid UI development. PostCSS is used for processing.
- **Language:** TypeScript (`tsconfig.json` & `vite.config.ts`) for strict typing and better developer experience.

## Running the Application
Ensure the FastAPI backend is running first so that the frontend can communicate with the APIs.

```bash
cd frontend/mapr1-app
npm install
npm run dev
```

The server will typically start on `http://localhost:5173`.

## Core Features (Visualizations)
The frontend application connects to the MapR1 API and visualizes several core data layers:
1. **Interactive Timelines (`frontend/timeline/`)**: View the step-by-step passage of time, significant narrative milestones, and global events.
2. **Entity Graphs (`frontend/graphs/`)**: Using node-based representations, you can visualize the complex web of relationships and tensions between agents, factions, and organizations.
3. **Map Views (`frontend/maps/`)**: Spatial visualizations of world states.
4. **Agent Inspection**: A detailed view into a specific agent's state, memories, goals, and internal diary logs to understand their decisions.

## API Integration
The frontend utilizes REST calls (and potentially WebSockets for the `Theater` simulation) to stream data from the backend. The backend URL must be correctly configured in the `.env` file of `mapr1-app`.

```env
VITE_API_URL=http://localhost:8000/api
```

## Additional Tools
There is also a separate `stitch_mapr1_dream_simulator/` frontend application for experimental Dream Mode interfaces.
