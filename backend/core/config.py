"""
MapR1 — Core Configuration
Loads all settings from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "MapR1"
    app_version: str = "0.1.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM Provider — set LLM_PROVIDER=groq, ollama, or openrouter
    llm_provider: str = "groq"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Ollama (local fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:4b"
    
        # OpenRouter (for scenario seeder creative generation)
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    theater_openrouter_model: str = "z-ai/glm-4.5-air:free"
    agent_openrouter_model: str = "openrouter/owl-alpha"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""
    
    # Database (Supabase PostgreSQL)
    database_url: str = ""

    # Simulation
    max_scenarios: int = 5
    max_timeline_events: int = 10
    scenario_temperature: float = 0.8
    max_tokens: int = 4000


settings = Settings()
