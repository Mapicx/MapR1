"""
MapR1 — Scenario Generator
Core logic for generating future scenarios using LLM with structured outputs.
"""

from typing import List

from loguru import logger

from backend.core.config import settings
from backend.models.llm_client import ollama_client
from backend.models.prompts import create_scenario_generation_prompt, create_system_prompt
from backend.models.scenario import (
    LLMScenariosResponse,
    Scenario,
    ScenarioCategory,
    TimelineEvent,
)


class ScenarioGenerator:
    """Generates future scenarios using LLM with structured outputs"""

    def __init__(self):
        self.llm = ollama_client
        self.system_prompt = create_system_prompt()

    async def generate_scenarios(
        self, user_input: str, num_scenarios: int = 3
    ) -> List[Scenario]:
        """
        Generate multiple future scenarios from user input using structured outputs

        Args:
            user_input: The user's scenario request
            num_scenarios: Number of scenarios to generate (1-5)

        Returns:
            List of generated Scenario objects

        Raises:
            Exception: If LLM generation fails
        """
        # Validate input
        num_scenarios = max(1, min(num_scenarios, settings.max_scenarios))

        logger.info(f"Generating {num_scenarios} scenarios for: {user_input[:50]}...")

        # Create prompt
        prompt = create_scenario_generation_prompt(user_input, num_scenarios)

        # Generate scenarios using structured output
        llm_response = await self.llm.generate_structured(
            prompt=prompt,
            response_model=LLMScenariosResponse,
            temperature=settings.scenario_temperature,
            system_prompt=self.system_prompt,
        )

        # Convert LLM response to Scenario objects
        scenarios = self._convert_to_scenarios(llm_response)

        if not scenarios:
            raise Exception("LLM generated empty response. No scenarios created.")

        logger.success(f"Successfully generated {len(scenarios)} scenarios")
        return scenarios

    def _convert_to_scenarios(self, llm_response: LLMScenariosResponse) -> List[Scenario]:
        """
        Convert LLM structured response to Scenario objects

        Args:
            llm_response: The structured response from LLM

        Returns:
            List of Scenario objects
        """
        scenarios = []

        for llm_scenario in llm_response.scenarios:
            try:
                # Convert timeline events
                timeline_events = [
                    TimelineEvent(
                        year=event.year,
                        description=event.description,
                        impact=event.impact,
                    )
                    for event in llm_scenario.timeline
                ]

                # Create scenario
                scenario = Scenario(
                    title=llm_scenario.title,
                    description=llm_scenario.description,
                    category=ScenarioCategory(llm_scenario.category.lower()),
                    probability=llm_scenario.probability,
                    timeline=timeline_events,
                )

                scenarios.append(scenario)

            except Exception as e:
                logger.warning(f"Failed to convert scenario: {e}")
                continue

        return scenarios


# Global generator instance
scenario_generator = ScenarioGenerator()
