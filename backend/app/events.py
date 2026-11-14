"""Experiment event adapters reuse the feature SDK and the same user context identity."""

from .domain import Profile


class PreviewEvents:
    """Preview actions never become real experiment conversions."""

    def track(self, key: str, profile: Profile, data: dict) -> bool:
        return False


# DEMO START experiment-events: Queue conversion events with the same context used for flag evaluation.
class LaunchDarklyEvents:
    """Queue custom metric events; SDK acceptance does not prove platform ingestion."""

    def __init__(self, features):
        self.features = features

    def track(self, key: str, profile: Profile, data: dict) -> bool:
        client = self.features.client
        if client is None or not client.is_initialized():
            return False
        # Re-create a custom metric with this EVENT key in LD; metric resource keys differ.
        # Reuse the evaluation context so conversion attribution uses the user randomization unit.
        client.track(key, self.features.context(profile), data)
        return True
# DEMO END experiment-events
