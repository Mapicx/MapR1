"""
MapR1 — Prompt Templates
Structured prompts for scenario generation.

Note: The Pydantic model structure is automatically added by Instructor,
so we only focus on content instructions, not format specifications.
"""

from typing import List


def create_scenario_generation_prompt(user_input: str, num_scenarios: int = 3) -> str:
    """
    Create a prompt for generating multiple future scenarios.
    
    The Pydantic model structure is automatically added by Instructor,
    so we only need to focus on the content instructions.

    Args:
        user_input: The user's scenario request
        num_scenarios: Number of scenarios to generate

    Returns:
        Formatted prompt string
    """
    prompt = f"""Generate {num_scenarios} distinct future scenarios based on this input:

"{user_input}"

Requirements for each scenario:
- Create diverse perspectives (optimistic, pessimistic, mixed)
- Provide a compelling title
- Write a clear 2-3 sentence description
- Include 5-7 chronological events with specific years
- Make scenarios plausible and internally consistent
- Consider second-order effects and unexpected consequences
- Ensure each scenario explores a different path

Focus on creating thought-provoking, realistic futures that help explore the possibility space."""

    return prompt


def create_system_prompt() -> str:
    """
    Create the system prompt for the LLM.
    
    The response format is automatically handled by Instructor,
    so we focus on the role and behavior.

    Returns:
        System prompt string
    """
    return """You are MapR1, an AI-powered imagination engine specialized in exploring possible futures and alternate realities.

Your purpose:
- Generate plausible future scenarios
- Think through consequences and second-order effects
- Create diverse perspectives (optimistic, pessimistic, mixed)
- Maintain internal consistency within each scenario
- Provide structured, actionable insights

You do NOT predict the future. You explore possibilities.

Be creative but grounded in plausibility. Consider how current trends, technologies, and social dynamics might evolve."""


def create_timeline_refinement_prompt(scenario_title: str, description: str) -> str:
    """
    Create a prompt to refine and expand a timeline.
    
    Note: This is for future use when we want to expand existing scenarios.

    Args:
        scenario_title: Title of the scenario
        description: Description of the scenario

    Returns:
        Formatted prompt string
    """
    prompt = f"""Given this future scenario, create a detailed timeline of events.

Scenario: {scenario_title}
Description: {description}

Generate 7-10 chronological events that show how this future unfolds:
- Specific years (realistic progression)
- Clear event descriptions
- Appropriate impact levels (high/medium/low)
- Logical cause-and-effect progression

Show how one event leads to the next, creating a coherent narrative arc."""

    return prompt


def create_scenario_analysis_prompt(scenario: dict) -> str:
    """
    Create a prompt to analyze a scenario's implications.
    
    Note: This is for future use in Phase 3+ when we add deeper analysis.

    Args:
        scenario: The scenario dictionary

    Returns:
        Formatted prompt string
    """
    prompt = f"""Analyze this future scenario and identify key implications:

Title: {scenario.get('title')}
Description: {scenario.get('description')}

Provide:
1. Key risks and vulnerabilities
2. Key opportunities and advantages
3. Critical decision points
4. Potential wildcards or black swan events
5. Recommended strategies for navigating this future

Focus on actionable insights."""

    return prompt
