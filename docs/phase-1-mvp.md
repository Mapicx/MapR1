# Phase 1: MVP - Basic Scenario Generation
**Timeline:** Week 1-2  
**Status:** Not Started

---

## Overview

Build the foundational system that can generate multiple hypothetical futures from a user prompt. This phase establishes the core architecture and proves the concept works.

---

## Goals

- ✅ Generate multiple hypothetical futures from user input
- ✅ Basic LLM integration working
- ✅ Simple API endpoints functional
- ✅ Basic timeline output format

---

## What We're Building

### 1. FastAPI Backend Setup

**Files to Create:**
- `main.py` - Application entry point
- `backend/api/routes.py` - API endpoints
- `backend/core/config.py` - Configuration management

**Implementation:**
```python
# Basic structure needed:
- POST /api/scenarios/generate
- GET /api/scenarios/{id}
- GET /api/health
```

**Requirements:**
- FastAPI framework
- Pydantic models for validation
- CORS middleware
- Basic error handling

---

### 2. LLM Integration

**Files to Create:**
- `backend/models/llm_client.py` - LLM wrapper
- `backend/models/prompts.py` - Prompt templates

**Implementation Details:**

**Choose LLM Runtime:**
- Ollama (recommended for local dev)
- llama.cpp
- vLLM

**Suggested Models:**
- Lightweight: Gemma, Phi, TinyLlama
- Better reasoning: LLaMA, Qwen, Mistral

**Core Functions:**
```python
def generate_scenarios(user_input: str) -> List[Scenario]:
    """Generate 3-5 alternate future scenarios"""
    pass

def format_prompt(input: str, context: dict) -> str:
    """Create structured prompts for scenario generation"""
    pass
```

---

### 3. Scenario Generator

**Files to Create:**
- `backend/reasoning/scenario_generator.py`
- `backend/models/scenario.py` - Data models

**What It Does:**
- Takes user input
- Generates 3-5 alternate futures
- Returns structured scenario data

**Data Structure:**
```python
class Scenario:
    id: str
    title: str
    description: str
    timeline: List[Event]
    probability: float
    category: str  # optimistic, pessimistic, mixed
```

**Example Flow:**
```
User: "What happens if AGI appears in 2035?"
↓
System generates:
- Scenario A: Optimistic (AI solves climate change)
- Scenario B: Dystopian (AI control wars)
- Scenario C: Mixed (Gradual adaptation)
```

---

### 4. Simple Timeline Output

**Files to Create:**
- `backend/reasoning/timeline_generator.py`

**What It Does:**
- Converts scenarios into chronological events
- Formats readable timeline

**Output Format:**
```json
{
  "scenario_id": "abc123",
  "events": [
    {
      "year": 2035,
      "description": "AGI breakthrough announced",
      "impact": "high"
    },
    {
      "year": 2036,
      "description": "First AI-designed city completed",
      "impact": "medium"
    }
  ]
}
```

---

## Technical Requirements

### Dependencies to Install

```toml
# pyproject.toml additions
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.25.0",
    "ollama>=0.1.0",  # or your chosen LLM client
]
```

### Environment Variables

```bash
# .env
LLM_MODEL=llama3
LLM_BASE_URL=http://localhost:11434
API_PORT=8000
LOG_LEVEL=INFO
```

---

## Implementation Steps

### Step 1: Project Setup (Day 1)
1. Initialize FastAPI application
2. Set up configuration management
3. Create basic health check endpoint
4. Test server runs successfully

### Step 2: LLM Integration (Day 2-3)
1. Install and configure Ollama (or chosen LLM)
2. Create LLM client wrapper
3. Test basic prompt/response
4. Create prompt templates for scenario generation

### Step 3: Scenario Generation (Day 4-5)
1. Implement scenario generator logic
2. Create Pydantic models for scenarios
3. Build structured prompt engineering
4. Test with various inputs

### Step 4: API Endpoints (Day 6-7)
1. Create POST /api/scenarios/generate endpoint
2. Add request validation
3. Implement response formatting
4. Add error handling

### Step 5: Timeline Generation (Day 8-9)
1. Build timeline generator
2. Convert scenarios to chronological events
3. Format output for readability
4. Test timeline coherence

### Step 6: Testing & Polish (Day 10)
1. Test end-to-end flow
2. Fix bugs
3. Add logging
4. Document API endpoints

---

## Testing Checklist

- [ ] Server starts without errors
- [ ] Health check endpoint responds
- [ ] LLM generates responses
- [ ] Scenario generation works with sample inputs
- [ ] API returns valid JSON
- [ ] Multiple scenarios are generated
- [ ] Timelines are chronologically ordered
- [ ] Error handling works for invalid inputs

---

## Success Criteria

**Phase 1 is complete when:**

1. User can send a prompt via API
2. System generates 3+ alternate future scenarios
3. Each scenario has a basic timeline
4. Results are returned in structured JSON
5. System is stable and doesn't crash

**Example Working Flow:**
```bash
curl -X POST http://localhost:8000/api/scenarios/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What happens if fusion energy becomes viable?"}'

# Returns:
{
  "scenarios": [
    {
      "id": "1",
      "title": "Energy Revolution",
      "timeline": [...]
    },
    {
      "id": "2", 
      "title": "Geopolitical Shift",
      "timeline": [...]
    }
  ]
}
```

---

## Known Limitations (To Address in Later Phases)

- ❌ No persistent storage (scenarios lost on restart)
- ❌ No world state tracking
- ❌ No agent simulation
- ❌ No branching logic
- ❌ No memory between requests
- ❌ No visualization
- ❌ No user interface

---

## Next Phase Preview

**Phase 2** will add:
- Database integration
- Persistent world state
- Entity tracking
- Memory system
- Branching logic

This will transform the system from a simple generator into a persistent simulation engine.

---

## Resources & References

**FastAPI Documentation:**
- https://fastapi.tiangolo.com/

**Ollama Setup:**
- https://ollama.ai/

**Prompt Engineering:**
- Focus on structured outputs
- Request JSON format
- Specify scenario diversity

**Example Prompt Template:**
```
Generate 3 distinct future scenarios for: {user_input}

For each scenario provide:
1. Title
2. Description (2-3 sentences)
3. Timeline (5 key events with years)
4. Overall tone (optimistic/pessimistic/mixed)

Format as JSON.
```

---

## Notes

- Keep it simple - don't over-engineer
- Focus on getting ONE thing working end-to-end
- Test with real LLM early
- Document what works and what doesn't
- Iterate quickly

**Remember:** This phase is about proving the concept works, not building the perfect system.
