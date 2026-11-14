"""Provider-independent data models shared by the API and application services."""

from typing import Literal

from pydantic import BaseModel, Field


class Profile(BaseModel):
    """Fictional visitor identity; its stable key and attributes drive targeting."""
    key: str
    name: str
    role: str
    tier: str
    geography: str = "India"
    beta_tester: bool = False
    experiment_eligible: bool = False


class Offer(BaseModel):
    id: str
    category: str
    title: str
    description: str
    highlight: str
    detail: str
    accent: str


class DemoState(BaseModel):
    """Local presentation controls; release overrides apply only in preview mode."""
    release: Literal["existing", "targeted", "new"] = "targeted"
    incident: bool = False


class Decision(BaseModel):
    """Keep the served variant, its origin, and fallback status explicit in the UI."""
    variant: Literal["existing", "new"]
    reason: str
    source: str = "Local preview"
    fallback: bool = False
    evaluation_reason: dict = Field(default_factory=dict)


class Engagement(BaseModel):
    profile_key: str
    offer_id: str


class ChatRequest(BaseModel):
    profile_key: str
    message: str = Field(min_length=1, max_length=1000)
