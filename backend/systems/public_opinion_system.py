from typing import Optional
from backend.models.world_models import StructuredWorldState

class PublicOpinionSystem:
    """
    Manages nonlinear public opinion dynamics.
    Public opinion shifts accelerate near tipping points and cross thresholds
    that produce distinct qualitative states.
    """
    
    # Generic thresholds map for public opinion topics (0.0 to 1.0)
    # The default assumption is that higher values = higher tension/panic.
    THRESHOLDS = [
        (0.0, "stable"),
        (0.3, "concerned"),
        (0.5, "fearful"),
        (0.7, "angry"),
        (0.85, "radicalized"),
        (0.95, "revolutionary")
    ]

    def push_opinion(self, world_state: StructuredWorldState, topic: str, delta: float) -> Optional[str]:
        """
        Shifts public opinion on a topic nonlinearly.
        Returns a descriptive event string if a threshold is crossed, else None.
        """
        current = world_state.public_opinion.get(topic, 0.0)
        
        # Nonlinear scaling: acceleration is higher when delta is in the direction of the extreme
        # We will use the formula: new = current + delta * (1 + abs(current - 0.5))
        # This means near 0 or 1, shifts are up to 1.5x faster.
        # However, to be more aggressive with tipping points:
        new = current + delta * (1.0 + abs(current - 0.5))
        
        # Clamp between 0 and 1
        new = max(0.0, min(1.0, new))
        
        world_state.public_opinion[topic] = new
        
        old_zone = self.get_zone(current)
        new_zone = self.get_zone(new)
        
        if old_zone != new_zone:
            # Did it go up or down?
            direction = "escalated to" if new > current else "de-escalated to"
            return f"Public opinion on '{topic}' has {direction} {new_zone.upper()}."
            
        return None

    def get_zone(self, value: float) -> str:
        """Get the qualitative label for a given numeric opinion value."""
        # Iterate backwards to find the highest threshold passed
        for threshold, label in reversed(self.THRESHOLDS):
            if value >= threshold:
                return label
        return self.THRESHOLDS[0][1]
