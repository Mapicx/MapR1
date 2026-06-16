import hashlib
from typing import List, Dict
from backend.models.theme_models import ThemeSpec
from backend.models.compiled_model import CompiledTheme

class ThemeCompiler:
    """
    Compiles a ThemeSpec into a canonical CompiledTheme.
    Normalizes domain-specific strings into stable keys and rejects malformed data.
    """
    
    def _create_mapping(self, prefix: str, items: List[str]) -> Dict[str, str]:
        if not items:
            raise ValueError(f"Theme specification is missing required {prefix} items.")
        
        # Sort items deterministically before assigning keys
        sorted_items = sorted(items)
        return {f"{prefix}_{i}": item for i, item in enumerate(sorted_items)}

    def compile(self, spec: ThemeSpec) -> CompiledTheme:
        """
        Compiles the ThemeSpec into a deterministic CompiledTheme.
        """
        try:
            conflicts = self._create_mapping("conflict", spec.core_conflicts)
            roles = self._create_mapping("role", spec.actor_roles)
            resources = self._create_mapping("resource", spec.resource_types)
            institutions = self._create_mapping("institution", spec.institution_types)
            events = self._create_mapping("event", spec.event_templates)
            victory_conditions = self._create_mapping("victory", spec.victory_conditions)
            failure_conditions = self._create_mapping("failure", spec.failure_conditions)
            
            if not spec.vocabulary_map:
                raise ValueError("Theme specification is missing a vocabulary map.")
                
            # Create a deterministic ID based on the theme name and contents
            content_hash = hashlib.md5(spec.theme_name.encode()).hexdigest()[:8]
            theme_id = f"theme_{content_hash}"
            
            return CompiledTheme(
                id=theme_id,
                theme_name=spec.theme_name,
                theme_summary=spec.theme_summary,
                narrative_tone=spec.narrative_tone,
                risk_profile=spec.risk_profile,
                conflicts=conflicts,
                roles=roles,
                resources=resources,
                institutions=institutions,
                events=events,
                victory_conditions=victory_conditions,
                failure_conditions=failure_conditions,
                vocabulary_map=spec.vocabulary_map
            )
        except Exception as e:
            raise ValueError(f"Failed to compile ThemeSpec: {str(e)}")

theme_compiler = ThemeCompiler()
