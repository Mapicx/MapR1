# MapR1 Frontend Setup Guide

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend/mapr1-app
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
# Copy the example env file
cp .env.example .env

# Edit .env if your backend runs on a different URL
# VITE_API_BASE_URL=http://localhost:8000/api
```

## Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```
src/
├── components/          # React components
│   ├── 3d/             # Three.js 3D components
│   │   └── ScenarioNodes.tsx
│   ├── ui/             # UI components
│   │   ├── TopBar.tsx
│   │   ├── LeftSidebar.tsx
│   │   └── RightSidebar.tsx
│   └── Scene3D.tsx     # Main 3D scene
├── services/           # API services
│   └── api.ts
├── stores/             # Zustand state management
│   ├── projectStore.ts
│   ├── scenarioStore.ts
│   └── simulationStore.ts
├── types/              # TypeScript types
│   └── index.ts
├── App.tsx             # Main app component
├── main.tsx            # Entry point
└── index.css           # Global styles
```

## Features

### Current Implementation

- ✅ Project management (create, select, switch)
- ✅ 3D visualization with Three.js
- ✅ Scenario nodes as floating spheres
- ✅ Color-coded by category (optimistic, pessimistic, mixed, neutral)
- ✅ Interactive node selection
- ✅ Scenario list with filtering
- ✅ Simulation controls (start, stop, step)
- ✅ Real-time status display
- ✅ Pattern detection panel
- ✅ Recent actions feed
- ✅ Cyber-tactical green theme with glass morphism

### Upcoming Features

- 🔄 Entity nodes visualization
- 🔄 Agent nodes as satellites
- 🔄 Relationship lines between agents
- 🔄 Action beam animations
- 🔄 Pattern overlay visualizations
- 🔄 Timeline scrubbing
- 🔄 Memory search interface
- 🔄 Goal tree visualization

## Design System

The app uses a **Cyber-Tactical Green** theme:

- **Primary Color:** Neon Green (#6bfb9a)
- **Background:** Obsidian Black (#0a0a0a, #131313)
- **Typography:** Inter (UI) + JetBrains Mono (data/labels)
- **Effects:** Glass morphism, scanlines, neon glow
- **Shape Language:** Sharp corners (0px radius)

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000/api`.

Key endpoints used:
- `/projects` - Project CRUD
- `/scenarios` - Scenario generation and management
- `/entities` - Entity management
- `/agents` - Agent management
- `/simulate` - Simulation control
- `/patterns` - Pattern detection

See `API_QUICK_REFERENCE.md` in the project root for complete API documentation.

## Troubleshooting

### Backend Connection Issues

If you see "Network Error" or connection refused:

1. Ensure the backend is running:
```bash
cd backend
uvicorn main:app --reload
```

2. Check the backend URL in `.env`:
```
VITE_API_BASE_URL=http://localhost:8000/api
```

3. Verify CORS is enabled in the backend (should be by default)

### 3D Scene Not Rendering

If the 3D scene is blank:

1. Check browser console for WebGL errors
2. Ensure your browser supports WebGL 2.0
3. Try disabling browser extensions that might block WebGL

### Slow Performance

If the app is slow:

1. Reduce the number of visible nodes in the 3D scene
2. Lower the simulation step frequency
3. Check if the backend LLM (Qwen) is responding slowly
4. Consider using a faster LLM model

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Three.js** - 3D graphics
- **React Three Fiber** - React renderer for Three.js
- **React Three Drei** - Three.js helpers
- **Zustand** - State management
- **React Query** - Server state management
- **Axios** - HTTP client
- **Tailwind CSS** - Styling

## Contributing

When adding new features:

1. Follow the existing component structure
2. Use TypeScript types from `src/types/index.ts`
3. Add API calls to `src/services/api.ts`
4. Use Zustand stores for state management
5. Follow the cyber-tactical design system
6. Keep components focused and composable

## License

Part of the MapR1 AI Imagination Engine project.
