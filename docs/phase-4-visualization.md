# Phase 4: Visualization & UI
**Timeline:** Week 7-8  
**Status:** Not Started  
**Prerequisites:** Phase 1, 2, 3 Complete

---

## Overview

Transform the backend simulation engine into an explorable, visual experience. This phase adds interactive timelines, world maps, relationship graphs, and a dashboard that makes complex simulations understandable and engaging.

**Key Concept:** Visualization turns data into insight. Without it, simulations remain abstract.

---

## Goals

- ✅ Interactive timeline visualization
- ✅ Future branching graph display
- ✅ Agent relationship network visualization
- ✅ World state dashboard
- ✅ Real-time simulation controls
- ✅ Responsive web interface

---

## What We're Building

### 1. Frontend Architecture

**Technology Choice:**

**Option A: React + Tailwind (Recommended)**
- Modern, flexible
- Rich ecosystem
- Good for complex UIs

**Option B: Next.js**
- Server-side rendering
- Better SEO
- Startup-friendly

**Option C: Streamlit**
- Fastest to build
- Python-native
- Limited customization

**Recommendation:** React + Tailwind for Phase 4

---

### 2. Core Visualizations

#### A. Timeline Visualization

**Files to Create:**
- `frontend/timeline/TimelineView.tsx`
- `frontend/timeline/EventCard.tsx`
- `frontend/timeline/TimelineControls.tsx`

**Features:**
- Chronological event display
- Zoom in/out on time periods
- Filter by event type
- Highlight critical events
- Scrub through time

**Library:** D3.js or Plotly

**Example Layout:**
```
┌─────────────────────────────────────────┐
│  Timeline: "AGI Future Scenario"        │
├─────────────────────────────────────────┤
│                                         │
│  2030 ●─────────────────────────────   │
│       AGI Breakthrough                  │
│                                         │
│  2032 ●─────────────────────────────   │
│       First AI-Designed City            │
│                                         │
│  2035 ●─────────────────────────────   │
│       Global AI Regulation Treaty       │
│                                         │
│  [◀] [▶] [⏸] [⏩]                      │
└─────────────────────────────────────────┘
```

---

#### B. Branching Future Graph

**Files to Create:**
- `frontend/graphs/BranchingGraph.tsx`
- `frontend/graphs/NodeDetail.tsx`

**Features:**
- Tree/network visualization of timeline branches
- Click nodes to explore branches
- Compare parallel timelines
- Highlight divergence points

**Library:** Cytoscape.js or D3.js

**Example Layout:**
```
        Main Timeline
             │
        2035: AGI
             │
        ┌────┴────┐
        │         │
   Branch A   Branch B
   Open AI    Corporate
        │         │
    ┌───┴───┐    │
    │       │    │
  A1: Peace A2: War B1: Monopoly
```

---

#### C. Agent Relationship Network

**Files to Create:**
- `frontend/graphs/RelationshipGraph.tsx`
- `frontend/graphs/AgentNode.tsx`

**Features:**
- Network graph of agents
- Edge colors show relationship type
  - Green: Alliance
  - Red: Enemy
  - Blue: Trade
  - Gray: Neutral
- Edge thickness shows relationship strength
- Click agents for details

**Library:** Cytoscape.js or vis.js

**Example:**
```
    [Nation A]────────[Nation B]
        │ ╲              │
        │  ╲             │
        │   ╲            │
    [Nation C]──────[Nation D]
    
    ──── Alliance
    ╌╌╌╌ Trade
    ~~~~ Enemy
```

---

#### D. World State Dashboard

**Files to Create:**
- `frontend/ui/Dashboard.tsx`
- `frontend/ui/WorldStats.tsx`
- `frontend/ui/AgentList.tsx`

**Features:**
- Current world statistics
- Agent status overview
- Recent events feed
- Resource levels
- Conflict indicators

**Example Layout:**
```
┌─────────────────────────────────────────┐
│  World: "Cyberpunk 2077"                │
├─────────────────────────────────────────┤
│  Stats:                                 │
│  ● Stability: 65%                       │
│  ● Economy: 72%                         │
│  ● Conflicts: 3 active                  │
│                                         │
│  Agents: 12                             │
│  ● 5 Nations                            │
│  ● 4 Companies                          │
│  ● 3 Factions                           │
│                                         │
│  Recent Events:                         │
│  • War declared (2 hours ago)           │
│  • Alliance formed (5 hours ago)        │
└─────────────────────────────────────────┘
```

---

#### E. World Map (Optional)

**Files to Create:**
- `frontend/maps/WorldMap.tsx`
- `frontend/maps/TerritoryLayer.tsx`

**Features:**
- Geographic visualization
- Territory control
- Resource distribution
- Conflict zones

**Library:** Leaflet or Mapbox

---

### 3. Simulation Controls

**Files to Create:**
- `frontend/ui/SimulationControls.tsx`

**Features:**
```
┌─────────────────────────────────────────┐
│  Simulation Controls                    │
├─────────────────────────────────────────┤
│  [▶ Play] [⏸ Pause] [⏹ Stop]          │
│                                         │
│  Speed: [1x] [2x] [5x] [10x]           │
│                                         │
│  Steps: [+1] [+10] [+100]              │
│                                         │
│  Auto-run: [ON] [OFF]                  │
└─────────────────────────────────────────┘
```

---

### 4. Interactive Features

#### A. Time Navigation

**Features:**
- Scrub through timeline
- Jump to specific dates
- Pause at key events
- Rewind and replay

#### B. Branch Creation

**Features:**
- Click event to create branch
- Modify decision
- Watch alternate future unfold
- Compare outcomes

#### C. Agent Inspection

**Features:**
- Click agent to view details
- See goals and progress
- View relationship history
- Inspect memory

#### D. Event Injection

**Features:**
- Add custom events
- Trigger scenarios
- Test "what if" questions
- Observe consequences

---

### 5. Frontend Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Timeline/
│   │   │   ├── TimelineView.tsx
│   │   │   ├── EventCard.tsx
│   │   │   └── TimelineControls.tsx
│   │   ├── Graphs/
│   │   │   ├── BranchingGraph.tsx
│   │   │   ├── RelationshipGraph.tsx
│   │   │   └── NodeDetail.tsx
│   │   ├── Dashboard/
│   │   │   ├── WorldStats.tsx
│   │   │   ├── AgentList.tsx
│   │   │   └── EventFeed.tsx
│   │   ├── Controls/
│   │   │   ├── SimulationControls.tsx
│   │   │   └── TimeControls.tsx
│   │   └── Maps/
│   │       └── WorldMap.tsx
│   ├── hooks/
│   │   ├── useSimulation.ts
│   │   ├── useWebSocket.ts
│   │   └── useWorldState.ts
│   ├── services/
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── types/
│   │   └── index.ts
│   └── App.tsx
├── package.json
└── tailwind.config.js
```

---

### 6. Real-Time Updates

**WebSocket Integration:**

**Backend:**
```python
# backend/api/websocket.py
from fastapi import WebSocket

@app.websocket("/ws/simulation/{world_id}")
async def simulation_websocket(websocket: WebSocket, world_id: str):
    await websocket.accept()
    
    while True:
        # Send world state updates
        state = get_world_state(world_id)
        await websocket.send_json(state)
        
        # Receive commands
        command = await websocket.receive_json()
        handle_command(command)
        
        await asyncio.sleep(1)
```

**Frontend:**
```typescript
// hooks/useWebSocket.ts
export function useWebSocket(worldId: string) {
  const [state, setState] = useState<WorldState>();
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/simulation/${worldId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setState(data);
    };
    
    return () => ws.close();
  }, [worldId]);
  
  return state;
}
```

---

### 7. API Integration

**Frontend API Client:**

```typescript
// services/api.ts
export class AetherMindAPI {
  private baseUrl = 'http://localhost:8000/api';
  
  async createWorld(name: string, description: string) {
    const response = await fetch(`${this.baseUrl}/worlds`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description })
    });
    return response.json();
  }
  
  async getWorld(worldId: string) {
    const response = await fetch(`${this.baseUrl}/worlds/${worldId}`);
    return response.json();
  }
  
  async simulateStep(worldId: string, steps: number = 1) {
    const response = await fetch(
      `${this.baseUrl}/worlds/${worldId}/simulate`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps })
      }
    );
    return response.json();
  }
  
  async getAgents(worldId: string) {
    const response = await fetch(
      `${this.baseUrl}/worlds/${worldId}/agents`
    );
    return response.json();
  }
  
  async createBranch(worldId: string, branchPoint: string) {
    const response = await fetch(
      `${this.baseUrl}/worlds/${worldId}/branch`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch_point: branchPoint })
      }
    );
    return response.json();
  }
}
```

---

## Implementation Steps

### Week 7

**Day 1-2: Frontend Setup**
1. Initialize React project
2. Install dependencies (D3, Cytoscape, Tailwind)
3. Set up routing
4. Create basic layout
5. Connect to backend API

**Day 3: Timeline Visualization**
1. Implement TimelineView component
2. Add D3.js timeline rendering
3. Create event cards
4. Add zoom/pan controls
5. Test with real data

**Day 4: Branching Graph**
1. Implement BranchingGraph component
2. Use Cytoscape.js for tree layout
3. Add node interaction
4. Create branch comparison view
5. Test branching visualization

**Day 5: Dashboard**
1. Create Dashboard layout
2. Implement WorldStats component
3. Add AgentList component
4. Create EventFeed component
5. Style with Tailwind

### Week 8

**Day 1: Relationship Graph**
1. Implement RelationshipGraph component
2. Add network visualization
3. Color-code relationships
4. Add agent detail view
5. Test with multiple agents

**Day 2: Simulation Controls**
1. Create SimulationControls component
2. Add play/pause/step functionality
3. Implement speed controls
4. Add auto-run toggle
5. Test control flow

**Day 3: WebSocket Integration**
1. Set up WebSocket connection
2. Implement real-time updates
3. Add state synchronization
4. Handle reconnection
5. Test live updates

**Day 4: Interactive Features**
1. Add time navigation
2. Implement branch creation UI
3. Add agent inspection
4. Create event injection interface
5. Test interactivity

**Day 5: Polish & Testing**
1. Responsive design
2. Error handling
3. Loading states
4. Performance optimization
5. End-to-end testing

---

## Technical Requirements

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "d3": "^7.8.5",
    "cytoscape": "^3.28.0",
    "cytoscape-react": "^2.0.0",
    "tailwindcss": "^3.3.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "recharts": "^2.10.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/d3": "^7.4.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0"
  }
}
```

### Backend WebSocket Support

```toml
[project]
dependencies = [
    # Existing...
    "websockets>=12.0",
]
```

---

## Testing Checklist

- [ ] Timeline displays events correctly
- [ ] Branching graph shows all timelines
- [ ] Relationship graph updates in real-time
- [ ] Dashboard shows accurate statistics
- [ ] Simulation controls work
- [ ] WebSocket connection stable
- [ ] Time navigation smooth
- [ ] Branch creation functional
- [ ] Agent inspection detailed
- [ ] Responsive on mobile
- [ ] Performance acceptable with large datasets

---

## Success Criteria

**Phase 4 is complete when:**

1. **Visual Exploration:**
   - Users can explore worlds visually
   
2. **Interactive Control:**
   - Users can control simulation flow
   
3. **Real-Time Updates:**
   - Changes appear immediately
   
4. **Intuitive Interface:**
   - Non-technical users can understand simulations

**Example User Flow:**
```
1. User opens dashboard
2. Sees world "Cyberpunk 2077"
3. Clicks timeline to view events
4. Notices conflict between nations
5. Clicks relationship graph
6. Sees alliance network
7. Creates branch: "What if peace treaty?"
8. Watches alternate future unfold
9. Compares outcomes
```

---

## Known Limitations (To Address in Future)

- ❌ No 3D visualization
- ❌ No VR/AR support
- ❌ No cinematic rendering
- ❌ No mobile app
- ❌ No collaborative features

---

## Next Phase Preview

**Phase 5** (Future) will add:
- Advanced AI features
- Recursive simulations
- Emotional agents
- Dream mode
- Autonomous evolution
- Self-generated universes

---

## Design Guidelines

### Color Scheme

```css
/* Recommended palette */
--primary: #6366f1;      /* Indigo */
--success: #10b981;      /* Green */
--danger: #ef4444;       /* Red */
--warning: #f59e0b;      /* Amber */
--neutral: #6b7280;      /* Gray */
--background: #0f172a;   /* Dark blue */
--surface: #1e293b;      /* Lighter dark */
```

### Typography

```css
/* Font stack */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Sizes */
--text-xs: 0.75rem;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
```

---

## Performance Considerations

### Optimization Strategies

1. **Virtual Scrolling** for long timelines
2. **Canvas Rendering** for large graphs (>100 nodes)
3. **Debounced Updates** for real-time data
4. **Lazy Loading** for components
5. **Memoization** for expensive calculations

### Target Metrics

- Initial load: < 2 seconds
- Time to interactive: < 3 seconds
- Frame rate: 60 FPS
- WebSocket latency: < 100ms

---

## Notes

- **Start with timeline** - Most important visualization
- **Test with real data** - Use actual simulation outputs
- **Mobile-first** - Design for small screens
- **Accessibility** - Keyboard navigation, screen readers
- **Performance** - Optimize early

**Key Insight:** Good visualization makes complex systems understandable. This is where the project becomes accessible to non-technical users.
