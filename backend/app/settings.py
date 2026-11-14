"""Server-only configuration: project-root .env, overridden by process environment."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


# DEMO START settings: Load server credentials privately from the root .env and validate live mode.
@dataclass(frozen=True)
class Settings:
    """Exclude credentials from the object's representation to avoid accidental logging."""
    mode: str = "preview"
    sdk_key: str = field(default="", repr=False)
    flag_key: str = "personalized-offers"
    flag_trigger_url: str = field(default="", repr=False)
    client_side_id: str = ""
    ai_enabled: bool = False
    ai_config_key: str = "offer-assistant"
    openai_key: str = field(default="", repr=False)

    @classmethod
    def from_environment(cls):
        # Resolve from the module location so IDE working-directory changes do not hide .env.
        values = {**dotenv_values(Path(__file__).resolve().parents[2] / ".env"), **os.environ}
        settings = cls(
            mode=values.get("APP_MODE", "preview"),
            # Replace LD_SDK_KEY in your local .env with your environment's server SDK key.
            # Never put that secret in React/VITE variables, source control, or API responses.
            sdk_key=values.get("LD_SDK_KEY", "") or "",
            # Re-create this Boolean flag in your own LD project, or set its actual key here via .env.
            flag_key=values.get("LD_OFFERS_FLAG_KEY", "personalized-offers") or "personalized-offers",
            # Copy the Test environment's Generic OFF trigger URL here via .env, never source code.
            # This URL authorizes flag changes without an API token; treat it as a secret.
            flag_trigger_url=values.get("LD_FLAG_TRIGGER_URL", "") or "",
            # This PUBLIC client-side ID belongs to the same Test environment; never use sdk- here.
            client_side_id=values.get("LD_CLIENT_SIDE_ID", "") or "",
            # Enable after creating the Completion config; never substitute the offers flag key.
            ai_enabled=values.get("AI_ENABLED", "false").lower() == "true",
            ai_config_key=values.get("LD_AI_CONFIG_KEY", "offer-assistant") or "offer-assistant",
            # OPENAI_API_KEY is server-only. No prompt, response body, or key belongs in telemetry.
            openai_key=values.get("OPENAI_API_KEY", "") or "",
        )
        if settings.mode not in {"preview", "launchdarkly"}:
            raise ValueError("APP_MODE must be preview or launchdarkly")
        if settings.mode == "launchdarkly" and not settings.sdk_key.strip():
            raise ValueError("Set LD_SDK_KEY in the project root .env before using LaunchDarkly mode")
        if settings.client_side_id and not settings.client_side_id.isalnum():
            raise ValueError("LD_CLIENT_SIDE_ID must be the public alphanumeric client-side ID, not a server SDK or mobile key")
        return settings
# DEMO END settings
