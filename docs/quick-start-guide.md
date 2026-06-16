# AetherMind Quick Start Guide

---

## What is AetherMind?

An AI-powered imagination engine that simulates hypothetical futures, generates alternate realities, and evolves persistent worlds with autonomous agents.

**Think:** World simulator + Future generator + Strategic imagination machine

---

## Quick Overview

### What It Does
- ✅ Generates multiple possible futures from a prompt
- ✅ Maintains persistent simulated worlds
- ✅ Simulates autonomous agents with goals
- ✅ Creates branching timelines
- ✅ Visualizes complex scenarios

### What It's NOT
- ❌ A chatbot
- ❌ A prediction system
- ❌ A simple Q&A tool

---

## 5-Minute Understanding

### Example Use Case

**Input:**
```
What happens if fusion energy becomes viable in 2030?
```

**System Generates:**

**Future A: Energy Revolution**
- 2030: Fusion breakthrough
- 2032: Oil economies collapse
- 2035: Rapid automation boom
- 2038: Space expansion era begins

**Future B: Geopolitical Conflict**
- 2030: Fusion breakthrough
- 2031: Energy wars begin
- 2033: Global instability
- 2036: New world order emerges

**Future C: Gradual Transition**
- 2030: Fusion breakthrough
- 2033: Slow adoption
- 2037: Mixed energy economy
- 2040: Steady progress

---

## Development Phases (Simple)

### Phase 1 (Weeks 1-2): Basic Generator
**Build:** API that generates future scenarios  
**Result:** Input prompt → Get 3-5 alternate futures

### Phase 2 (Weeks 3-4): Persistent Worlds
**Build:** Database + world state tracking  
**Result:** Worlds persist across sessions

### Phase 3 (Weeks 5-6): Autonomous Agents
**Build:** Agents with goals and decision-making  
**Result:** Agents form alliances, declare wars autonomously

### Phase 4 (Weeks 7-8): Visualization
**Build:** Interactive web interface  
**Result:** Visual exploration of simulations

### Phase 5 (Future): Advanced AI
**Build:** Emergent intelligence features  
**Result:** Dream mode, recursive simulations, emotional agents

---

## Tech Stack (Simple)

**Backend:**
- Python + FastAPI
- PostgreSQL (database)
- Ollama (local LLM)

**Frontend:**
- React + Tailwind
- D3.js (visualizations)

**AI:**
- LLaMA or Mistral models
- ChromaDB (memory)

---

## File Structure (Simple)

```
aethermind/
├── backend/          # Python API
├── frontend/         # React UI
├── database/         # PostgreSQL
├── docs/            # Documentation (you are here)
├── tests/           # Testing
└── main.py          # Entry point
```

---

## Getting Started

### 1. Install Prerequisites
```bash
# Python 3.11+
python --version

# Ollama (for LLM)
curl -fsSf https://ollama.com/install.sh | sh

# PostgreSQL
# (Install for your OS)

# Node.js 18+ (for frontend)
node --version
```

### 2. Clone & Setup
```bash
# Clone repo
git clone <repo-url>
cd aethermind

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services
```bash
# Terminal 1: Start Ollama
ollama serve
ollama pull llama3

# Terminal 2: Start backend
python main.py

# Terminal 3: Start frontend (later phases)
cd frontend
npm run dev
```

### 4. Test It
```bash
# Test API
curl -X POST http://localhost:8000/api/scenarios/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What if AGI appears in 2035?"}'
```

---

## Key Concepts

### 1. Scenarios
Possible future outcomes generated from a prompt.

### 2. Worlds
Persistent simulation environments with state.

### 3. Agents
Autonomous entities (nations, people, companies) with goals.

### 4. Timelines
Chronological sequences of events.

### 5. Branches
Alternate reality splits from decision points.

### 6. Memory
System that stores and recalls past events.

---

## Common Questions

### Q: Is this a chatbot?
**A:** No. It's a simulation engine that explores possibilities, not a conversational AI.

### Q: Does it predict the future?
**A:** No. It generates plausible scenarios, not predictions.

### Q: What can I use it for?
**A:** 
- Startup strategy exploration
- Creative worldbuilding
- Strategic planning
- Future scenario analysis
- Research and experimentation

### Q: How accurate are the simulations?
**A:** They're not meant to be accurate predictions, but plausible explorations of possibility space.

### Q: Can I customize the physics/rules?
**A:** Yes (in Phase 5) - you can define custom world rules.

---

## Next Steps

### For Developers
1. Read **[Implementation Roadmap](./implementation-roadmap.md)**
2. Start with **[Phase 1 Guide](./phase-1-mvp.md)**
3. Follow phase-by-phase implementation

### For Users (Future)
1. Wait for Phase 4 (UI) completion
2. Access web interface
3. Create worlds and explore scenarios

### For Contributors
1. Check open issues
2. Read phase documentation
3. Submit PRs following guidelines

---

## Documentation Index

- **[Implementation Roadmap](./implementation-roadmap.md)** - Complete overview
- **[Phase 1: MVP](./phase-1-mvp.md)** - Basic scenario generation
- **[Phase 2: Persistent Worlds](./phase-2-persistent-worlds.md)** - World state & memory
- **[Phase 3: Agent Simulation](./phase-3-agent-simulation.md)** - Autonomous agents
- **[Phase 4: Visualization](./phase-4-visualization.md)** - Interactive UI
- **[Phase 5: Advanced Features](./phase-5-advanced-features.md)** - Emergent intelligence

---

## Example Scenarios to Try

### Startup Simulation
```
What happens if I build an AI coding assistant?
```

### Civilization Simulation
```
Simulate a world where three nations compete for resources.
```

### Personal Planning
```
What are possible outcomes if I spend 3 years learning AI?
```

### Creative Worldbuilding
```
Generate a sci-fi universe with competing factions.
```

---

## Support

- **Documentation:** Check `/docs` folder
- **Issues:** Open GitHub issues
- **Questions:** Review phase guides first

---

## Project Status

**Current Phase:** Planning  
**Next Milestone:** Phase 1 MVP (Week 2)  
**Version:** 0.1.0

---

**Remember:** Start simple, iterate fast, build complexity gradually.

The goal is not to build AGI immediately, but to create a foundation for exploring computational imagination.
