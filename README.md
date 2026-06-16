# MapR1 — AI Imagination Engine

MapR1 is a computational imagination system and world simulation engine. Rather than acting as a standard chatbot answering questions, MapR1 explores "What could happen?" by simulating branching timelines, autonomous agents, and tracking tension and emergent behaviors.

## 🎯 What is MapR1?
MapR1 generates and simulates plausible future scenarios and alternate realities.
- **Scenario Seeding**: Translates a prompt (e.g., "What if AGI is achieved by 2029?") into a rich narrative theme and DNA for a project.
- **World Simulation**: Builds persistent worlds using SQLAlchemy/AsyncPG.
- **Simulation Theater**: Runs events and autonomous agent actions in real-time.
- **Agent Diaries**: Records inner monologues and thoughts for entities in the simulation using Vector Memory (ChromaDB).
- **Story Compiler**: Compiles the simulation events into cohesive narrative documents and chapter summaries.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for fast dependency management
- An LLM Provider (Ollama or Groq based on your `.env`)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd MapR1
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure the environment:**
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to select your LLM provider and API keys.*

4. **Run the Full Experience CLI:**
   You can run the entire lifecycle from seeding to story compilation using the CLI entry point:
   ```bash
   python run_full_experience.py --prompt "What if humanity discovers a parallel universe?" --steps 3
   ```
   *Check the `output/` directory for generated stories and agent diaries!*

5. **Start the API Server:**
   ```bash
   python main.py
   ```
   *The FastAPI server will be available at `http://localhost:8000`. API docs can be viewed at `http://localhost:8000/docs`.*

6. **Start the Frontend (Optional):**
   ```bash
   cd frontend/mapr1-app
   npm install
   npm run dev
   ```

## 📚 Documentation
For detailed insights into MapR1's architecture and modules, refer to our comprehensive documentation:

- **[Architecture & Design](file:///d:/MapR1/docs/ARCHITECTURE.md)** - Deep dive into the backend modules, simulation loops, and vector memory.
- **[Frontend Overview](file:///d:/MapR1/docs/FRONTEND.md)** - Details on the React/Vite interface and its capabilities.
- **[API Reference](file:///d:/MapR1/docs/API_REFERENCE.md)** - Documentation for the FastAPI REST endpoints.

## 🛠️ Tech Stack
- **Backend:** Python 3.11, FastAPI, Pydantic, SQLAlchemy, AsyncPG
- **AI/LLM:** Ollama, Groq, PyTorch, Transformers, ChromaDB, Sentence-Transformers
- **Simulation:** SimPy, NetworkX, Loguru
- **Frontend:** React, Vite, Tailwind CSS

---