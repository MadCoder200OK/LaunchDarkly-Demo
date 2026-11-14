"""Assemble the customer experience using interfaces rather than SDK-specific logic."""

from .catalog import OFFERS, PROFILES
from .domain import DemoState
from .ports import ActivitySink, AssistantProvider, FeatureProvider


# DEMO START experience-service: Compose offers and incident behavior through SDK-independent service interfaces.
class DemoService:
    def __init__(self, features: FeatureProvider, activity: ActivitySink, assistant: AssistantProvider):
        self.features = features
        self.activity = activity
        self.assistant = assistant
        self.state = DemoState()

    def profile(self, key: str):
        return next((profile for profile in PROFILES if profile.key == key), None)

    def view(self, profile):
        # Incident simulation affects only the new panel, so rollback restores the safe path.
        decision = self.features.evaluate(profile, self.state)
        return {"profile": profile, "decision": decision, "offers": OFFERS, "incident": self.state.incident and decision.variant == "new", "mode": self.features.mode, "integration": self.features.status()}
# DEMO END experience-service
