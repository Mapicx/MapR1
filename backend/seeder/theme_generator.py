from backend.models.theme_models import ThemeSpec
from backend.models.llm_client import llm_client
from pydantic import ValidationError
from loguru import logger

class ThemeGenerator:
    """
    Generates a domain-agnostic ThemeSpec from a raw dream seed.
    Runs as a pre-processing step before Pass 0 to establish genre rules.
    """
    
    def __init__(self):
        self.system_prompt = (
            "You are a master world-builder and simulation designer. "
            "Your task is to take a raw, unstructured user prompt (a 'dream seed') "
            "and convert it into a strictly structured ThemeSpec. "
            "Do NOT introduce domain-specific biases unless specified in the dream seed. "
            "For example, if the prompt is about fantasy, output fantasy roles and resources. "
            "Infer the domain, actor roles, resource types, institutions, core conflicts, "
            "event templates, narrative tone, vocabulary map, win/loss conditions, and risk profile. "
            "Keep the output abstract and meta-level (genre rules), rather than specific story instances."
        )
        
    async def generate_theme(self, dream_seed: str) -> ThemeSpec:
        """
        Takes a raw user dream prompt and converts it into a validated ThemeSpec.
        """
        try:
            logger.info(f"Generating ThemeSpec for seed: '{dream_seed[:50]}...'")
            theme_spec = await llm_client.generate_structured(
                prompt=dream_seed,
                response_model=ThemeSpec,
                system_prompt=self.system_prompt,
                temperature=0.7
            )
            logger.success(f"ThemeSpec generated successfully: {theme_spec.theme_name}")
            return theme_spec
        except ValidationError as e:
            logger.error(f"ThemeSpec validation failed: {e}")
            raise Exception(f"Failed to generate a valid ThemeSpec: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating ThemeSpec: {e}")
            raise

theme_generator = ThemeGenerator()
