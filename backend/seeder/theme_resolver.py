from typing import Dict, Any
from backend.models.compiled_model import CompiledTheme

class ThemeResolver:
    """
    Utility boundary for resolving canonical theme keys (e.g., 'role_0', 'resource_1') 
    back into human-readable display strings. Ensures resolution logic is decoupled 
    from individual generation passes and the simulation core.
    """
    
    def __init__(self, theme: CompiledTheme):
        self.theme = theme

    def resolve_role(self, key: str) -> str:
        return self.theme.roles.get(key, key)
        
    def resolve_resource(self, key: str) -> str:
        return self.theme.resources.get(key, key)
        
    def resolve_institution(self, key: str) -> str:
        return self.theme.institutions.get(key, key)
        
    def resolve_conflict(self, key: str) -> str:
        return self.theme.conflicts.get(key, key)
        
    def resolve_event(self, key: str) -> str:
        return self.theme.events.get(key, key)
        
    def resolve_victory(self, key: str) -> str:
        return self.theme.victory_conditions.get(key, key)
        
    def resolve_failure(self, key: str) -> str:
        return self.theme.failure_conditions.get(key, key)

    def resolve_text(self, text: str) -> str:
        """
        Replaces abstract tokens like {resource_1} with their resolved domain string.
        """
        if not text:
            return text
            
        import re
        
        def repl(match):
            key = match.group(1)
            # Try resources first
            val = self.theme.resources.get(key)
            if val: return val
            val = self.theme.roles.get(key)
            if val: return val
            val = self.theme.institutions.get(key)
            if val: return val
            val = self.theme.conflicts.get(key)
            if val: return val
            val = self.theme.events.get(key)
            if val: return val
            # Special keys
            if key == "displaced_units":
                # Assuming this might be mapped in vocabulary, otherwise return a default
                return self.theme.vocabulary_map.get("displaced_units", "displaced units")
            return match.group(0) # don't replace if not found
            
        # Match anything inside curly braces that looks like an abstract key
        return re.sub(r'\{([a-zA-Z0-9_]+)\}', repl, text)
