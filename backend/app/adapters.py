"""Local preview adapters; none of these implementations send data to LaunchDarkly."""

from collections import deque
from datetime import datetime, timezone

from .domain import Decision, DemoState, Profile


# DEMO START preview-flags: Provide credential-free preview targeting without sending cloud evaluations.
class PreviewFeatures:
    """Rehearse targeting locally; live targeting belongs in LaunchDarklyFeatures."""
    mode = "preview"

    def start(self, on_change):
        pass

    def status(self):
        return {"initialized": False, "connected": False, "state": "preview", "flag_key": None}

    def close(self):
        pass

    def evaluate(self, profile: Profile, state: DemoState) -> Decision:
        if state.release == "existing":
            return Decision(variant="existing", reason="Existing experience selected")
        if state.release == "new":
            return Decision(variant="new", reason="New experience selected for everyone")
        if profile.key == "qa-001":
            return Decision(variant="new", reason="Individual preview target: qa-001")
        if profile.tier == "Premium":
            return Decision(variant="new", reason="Preview rule: tier is Premium")
        return Decision(variant="existing", reason="Default: existing experience")
# DEMO END preview-flags


# DEMO START activity-feed: Keep a bounded local presenter feed separate from LaunchDarkly telemetry.
class LocalActivity:
    """Bound memory usage; this feed is not an experiment report or observability store."""
    def __init__(self):
        self.entries = deque(maxlen=60)

    def record(self, name: str, **attributes: str) -> None:
        self.entries.appendleft({"name": name, "time": datetime.now(timezone.utc).isoformat(), "attributes": attributes})
# DEMO END activity-feed


# DEMO START preview-ai: Return clearly scripted answers when live AI is disabled or unavailable.
class PreviewAssistant:
    """Clearly labeled scripted responses; no LLM or AI Config is evaluated here."""
    def reply(self, message: str, profile: Profile) -> str:
        query = message.lower()
        if any(word in query for word in ["travel", "card", "reward"]):
            return "The fictional ABC Voyager Card offers 3× reward points on travel. Select ‘Explore offer’ on the travel card to see its demo details."
        if any(word in query for word in ["sav", "goal", "fee"]):
            return "Goal Saver is our fictional savings offer with zero monthly account fees. It gives your next milestone a dedicated place to grow."
        return "I can help you explore our fictional travel, savings, and everyday banking offers. Try asking ‘Tell me about travel rewards’ or ‘How does Goal Saver work?’"

    async def start(self):
        pass

    async def close(self):
        pass

    def status(self):
        return {"status": "scripted", "config_key": None}

    async def respond(self, message: str, profile: Profile) -> dict:
        return {"reply": self.reply(message, profile), "source": "Scripted preview · no model connected", "fallback": True}
# DEMO END preview-ai
