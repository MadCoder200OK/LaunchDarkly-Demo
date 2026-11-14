"""Integration contracts that keep provider-specific SDK objects out of domain logic."""

from typing import Callable, Protocol

from .domain import Decision, DemoState, Profile


class FeatureProvider(Protocol):
    """Own SDK lifecycle, flag decisions, connection status, and change notifications."""
    mode: str

    def start(self, on_change: Callable[[], None]) -> None: ...

    def evaluate(self, profile: Profile, state: DemoState) -> Decision: ...

    def status(self) -> dict: ...

    def close(self) -> None: ...


class ActivitySink(Protocol):
    """Record application activity without tying callers to a telemetry vendor."""
    def record(self, name: str, **attributes: str) -> None: ...


class AssistantProvider(Protocol):
    """Allow a real AI adapter to replace scripted responses independently."""
    async def start(self) -> None: ...

    async def close(self) -> None: ...

    async def respond(self, message: str, profile: Profile) -> dict: ...

    def status(self) -> dict: ...


class EventTracker(Protocol):
    """Send business events independently from local logs and observability diagnostics."""

    def track(self, key: str, profile: Profile, data: dict) -> bool: ...
