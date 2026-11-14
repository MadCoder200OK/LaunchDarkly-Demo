"""Python SDK adapter; release and targeting decisions come from LaunchDarkly.

Official setup: https://launchdarkly.com/docs/sdk/server-side/python
Listener contract: https://launchdarkly.com/docs/sdk/features/flag-changes
"""

from ldclient import Context
from ldclient.client import LDClient
from ldclient.config import Config

from .domain import Decision, DemoState, Profile


class LaunchDarklyFeatures:
    """One long-lived SDK client per application process, not one per request."""
    mode = "launchdarkly"

    def __init__(self, settings, client_factory=LDClient):
        self.settings = settings
        self.client_factory = client_factory
        self.client = None
        self.on_change = lambda: None

    # DEMO START sdk-client: Initialize one streaming Python SDK client per server process.
    def start(self, on_change):
        # Settings reads LD_SDK_KEY from the server's .env; no credential is hard-coded here.
        # FastAPI starts this blocking initialization on a worker thread during its lifespan.
        self.on_change = on_change
        self.client = self.client_factory(Config(self.settings.sdk_key, stream=True), start_wait=5)
        self.client.flag_tracker.add_listener(self._flag_changed)
        self.client.data_source_status_provider.add_listener(self._status_changed)
    # DEMO END sdk-client

    # DEMO START flag-listener: Re-evaluate open visitor views when the offers flag changes.
    def _flag_changed(self, event):
        # Notifications identify a flag, not a per-user value; re-evaluate each open visitor view.
        if event.key == self.settings.flag_key:
            self.on_change()
    # DEMO END flag-listener

    # DEMO START sdk-status-listener: Publish SDK connectivity changes to open visitor views.
    def _status_changed(self, status):
        self.on_change()
    # DEMO END sdk-status-listener

    # DEMO START context: Build stable user contexts with the exact targeting attributes and types.
    def context(self, profile):
        # Rule attributes must match the names and types configured in the LD targeting UI.
        return (
            Context.builder(profile.key)
            .name(profile.name)
            .set("tier", profile.tier)
            .set("geography", profile.geography)
            .set("beta_tester", profile.beta_tester)
            .set("experiment_eligible", profile.experiment_eligible)
            .build()
        )
    # DEMO END context

    # DEMO START flag-evaluation: Evaluate the Boolean offers flag with a safe false fallback and a reason.
    def evaluate(self, profile: Profile, state: DemoState) -> Decision:
        # Deliberately ignore local state.release: it must never override a real LD decision.
        if self.client is None:
            return Decision(variant="existing", reason="SDK not started; safe fallback", source="LaunchDarkly fallback", fallback=True)
        # Re-create personalized-offers (or LD_OFFERS_FLAG_KEY) as a Boolean flag.
        # false is the SDK fallback; configure the flag's off variation separately as false.
        detail = self.client.variation_detail(self.settings.flag_key, self.context(profile), False)
        reason = dict(detail.reason)
        # A wrong flag type must not accidentally enable the new panel through truthiness.
        valid_type = type(detail.value) is bool
        fallback = detail.is_default_value() or not valid_type
        if not valid_type:
            reason = {"kind": "ERROR", "errorKind": "WRONG_TYPE"}
        return Decision(
            variant="new" if detail.value is True and not fallback else "existing",
            reason=reason.get("kind", "UNKNOWN") + (": " + reason["errorKind"] if "errorKind" in reason else ""),
            source="LaunchDarkly fallback" if fallback else "LaunchDarkly",
            fallback=fallback,
            evaluation_reason=reason,
        )
    # DEMO END flag-evaluation

    # DEMO START sdk-status: Distinguish initialized cached data from a currently connected SDK stream.
    def status(self):
        # Initialization means cached data exists; only a VALID stream means currently connected.
        if self.client is None:
            return {"initialized": False, "connected": False, "state": "not_started", "flag_key": self.settings.flag_key}
        state = self.client.data_source_status_provider.status.state.name.lower()
        return {"initialized": self.client.is_initialized(), "connected": state == "valid", "state": state, "flag_key": self.settings.flag_key}
    # DEMO END sdk-status

    # DEMO START sdk-cleanup: Remove listeners and close the shared feature SDK on shutdown.
    def close(self):
        # Unregister listeners and flush queued SDK events before shutting down the client.
        if self.client is not None:
            self.client.flag_tracker.remove_listener(self._flag_changed)
            self.client.data_source_status_provider.remove_listener(self._status_changed)
            self.client.flush()
            self.client.close()
            self.client = None
    # DEMO END sdk-cleanup
