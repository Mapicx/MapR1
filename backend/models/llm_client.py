"""
MapR1 — LLM Client
Unified client supporting multiple LLM providers (Groq, Ollama).
Switch providers by setting LLM_PROVIDER in .env:
  LLM_PROVIDER=groq   → uses Groq cloud API (llama-3.3-70b by default)
  LLM_PROVIDER=ollama → uses local Ollama instance
"""

import httpx
import instructor
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Type, TypeVar

from backend.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Provider-agnostic LLM client with structured output support.
    Configured via LLM_PROVIDER env var.
    """

    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self._setup_client()

    def _setup_client(self):
        if self.provider == "groq":
            self.model = settings.groq_model
            self.timeout = 60.0
            self.client = instructor.from_openai(
                OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=settings.groq_api_key,
                ),
                mode=instructor.Mode.JSON,
            )
            logger.info(f"LLM provider: Groq | model: {self.model}")

        elif self.provider == "ollama":
            self.model = settings.ollama_model
            self.timeout = 120.0
            self.client = instructor.from_openai(
                OpenAI(
                    base_url=f"{settings.ollama_base_url}/v1",
                    api_key="ollama",
                ),
                mode=instructor.Mode.JSON,
            )
            logger.info(f"LLM provider: Ollama | model: {self.model}")

        elif self.provider == "openrouter":
            self.model = getattr(settings, "agent_openrouter_model", "openrouter/owl-alpha")
            self.timeout = 120.0
            self.client = instructor.from_openai(
                OpenAI(
                    base_url=settings.openrouter_base_url,
                    api_key=settings.openrouter_api_key,
                ),
                mode=instructor.Mode.JSON,
            )
            logger.info(f"LLM provider: OpenRouter | model: {self.model}")

        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.provider}'. Use 'groq' or 'ollama'."
            )

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate structured output using a Pydantic response model."""
        if max_tokens is None:
            max_tokens = settings.max_tokens

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            logger.info(f"[{self.provider}] Generating structured output with {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.success("Structured output generated successfully")
            return response
        except Exception as e:
            logger.error(f"[{self.provider}] Structured generation failed: {e}")
            raise Exception(f"Failed to generate structured output: {str(e)}")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate plain text. Uses Ollama's native API for Ollama, chat completions for Groq."""
        if self.provider == "ollama":
            return await self._generate_ollama(prompt, temperature, max_tokens, system_prompt)
        else:
            return await self._generate_chat(prompt, temperature, max_tokens, system_prompt)

    async def _generate_chat(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
    ) -> str:
        """Plain text generation via OpenAI-compatible chat completions (Groq)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            # Use the underlying OpenAI client directly (not instructor)
            raw_client = self.client._client  # instructor wraps OpenAI
            response = raw_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"[{self.provider}] Text generation failed: {e}")
            raise Exception(f"LLM generation failed: {str(e)}")

    async def _generate_ollama(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
    ) -> str:
        """Plain text generation via Ollama's native /api/generate endpoint."""
        url = f"{settings.ollama_base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"[ollama] Generating with {self.model}")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                generated_text = response.json().get("response", "")
                logger.success(f"Generated {len(generated_text)} characters")
                return generated_text
        except httpx.TimeoutException:
            raise Exception("Ollama request timed out. Please try again.")
        except httpx.HTTPError as e:
            raise Exception(f"Failed to communicate with Ollama: {str(e)}")
        except Exception as e:
            raise Exception(f"LLM generation failed: {str(e)}")

    async def check_health(self) -> bool:
        """Check if the configured LLM provider is reachable and the model is available."""
        if self.provider == "groq":
            return await self._health_groq()
        elif self.provider == "ollama":
            return await self._health_ollama()
        return False

    async def _health_groq(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                )
                response.raise_for_status()
                models = [m["id"] for m in response.json().get("data", [])]
                if self.model in models:
                    logger.info(f"Groq healthy. Model '{self.model}' available.")
                    return True
                logger.warning(f"Model '{self.model}' not found on Groq. Available: {models}")
                return False
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False

    async def _health_ollama(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                response.raise_for_status()
                models = [m.get("name", "") for m in response.json().get("models", [])]
                if self.model in models:
                    logger.info(f"Ollama healthy. Model '{self.model}' available.")
                    return True
                logger.warning(f"Model '{self.model}' not found. Available: {models}")
                return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


# Global client instance — used across the app
llm_client = LLMClient()

# Backward-compat alias so existing imports don't break
ollama_client = llm_client
