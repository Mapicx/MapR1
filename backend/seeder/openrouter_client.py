"""
MapR1 — OpenRouter LLM Client

Dedicated client for OpenRouter API used by the scenario seeder.
Uses instructor for structured Pydantic outputs.
"""

import instructor
from openai import AsyncOpenAI
from typing import TypeVar, Type
from pydantic import BaseModel
from loguru import logger
from backend.core.config import settings

T = TypeVar('T', bound=BaseModel)


class OpenRouterClient:
    """Client for OpenRouter API with structured Pydantic outputs."""
    
    def __init__(self, model_name: str = None):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = model_name or settings.openrouter_model
        
        if not self.api_key:
            logger.warning("OpenRouter API key not configured. Seeder will not work.")
            self.client = None
        else:
            # Create OpenAI-compatible client for OpenRouter
            openai_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=180.0,  # 3 minutes timeout to allow for slow generations but prevent infinite hangs
            )
            
            # Wrap with instructor for structured outputs
            self.client = instructor.from_openai(
                openai_client,
                mode=instructor.Mode.JSON,
            )
    
    async def generate_structured(
        self,
        response_model: Type[T],
        prompt: str,
        system_prompt: str,
        temperature: float = 0.8,
        max_tokens: int = None,
    ) -> T:
        """
        Generate structured output using Pydantic model.
        
        Args:
            response_model: Pydantic model class for the response
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Instance of response_model with parsed data
        """
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "response_model": response_model,
                "temperature": temperature,
                "max_retries": 5,
            }
            
            # Only add max_tokens if explicitly provided and not None
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
                
            response = await self.client.chat.completions.create(**kwargs)
            
            logger.debug(f"OpenRouter structured generation completed for {response_model.__name__}")
            
            return response
        
        except Exception as e:
            logger.error(f"OpenRouter structured generation failed: {e}")
            raise


# Global instance
openrouter_client = OpenRouterClient()
