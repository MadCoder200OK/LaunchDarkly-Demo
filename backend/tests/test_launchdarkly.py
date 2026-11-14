"""Exercise the real SDK with an in-memory source; no account or credentials are used."""

import asyncio
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from ldclient.client import LDClient
from ldclient.config import Config
from ldclient.integrations.test_data import TestData

from app.catalog import PROFILES
from app.domain import DemoState
from app.launchdarkly_features import LaunchDarklyFeatures
from app.live_updates import LiveUpdates
from app.main import create_app
from app.settings import Settings


@pytest.fixture
def sdk():
    """Inject SDK test data rather than replacing the SDK evaluation algorithm with a mock."""
    data = TestData()
    data.update(data.flag("personalized-offers").variation_for_all(False))
    settings = Settings(mode="launchdarkly", sdk_key="sdk-test-only")

    def factory(config, start_wait):
        return LDClient(Config("sdk-test-only", update_processor_class=data, send_events=False, diagnostic_opt_out=True))

    provider = LaunchDarklyFeatures(settings, client_factory=factory)
    yield data, provider
    provider.close()


def test_real_sdk_targeting_and_rollback(sdk):
    """Verify SDK evaluation using test data; custom test sources do not emit stream callbacks."""
    data, provider = sdk
    changed = Event()
    provider.start(changed.set)
    flag = data.flag("personalized-offers").fallthrough_variation(False).variation_for_user("qa-001", True)
    flag.if_match("tier", "Premium").then_return(True)
    data.update(flag)
    expected = [("new", "TARGET_MATCH"), ("new", "RULE_MATCH"), ("existing", "FALLTHROUGH"), ("existing", "FALLTHROUGH")]
    for profile, (variant, reason) in zip(PROFILES, expected):
        decision = provider.evaluate(profile, DemoState(release="new"))
        assert decision.variant == variant
        assert decision.reason == reason
        assert not decision.fallback
    changed.clear()
    data.update(data.flag("personalized-offers").on(False).off_variation(False))
    assert provider.evaluate(PROFILES[0], DemoState()).reason == "OFF"
    assert provider.evaluate(PROFILES[0], DemoState()).variant == "existing"


def test_listener_filters_unrelated_flags(sdk):
    """Test callback routing separately from SDK test-data evaluation and live account streaming."""
    data, provider = sdk
    changed = Event()
    provider.start(changed.set)
    provider._flag_changed(SimpleNamespace(key="another-flag"))
    assert not changed.is_set()
    provider._flag_changed(SimpleNamespace(key="personalized-offers"))
    assert changed.is_set()


def test_safe_fallbacks(sdk):
    """Missing flags, unstarted SDKs, and non-Boolean variations must serve the old panel."""
    data, provider = sdk
    assert provider.evaluate(PROFILES[0], DemoState()).fallback
    provider.start(lambda: None)
    data.update(data.flag("personalized-offers").variations("enabled", "disabled").variation_for_all(0))
    decision = provider.evaluate(PROFILES[0], DemoState())
    assert decision.variant == "existing"
    assert decision.reason == "ERROR: WRONG_TYPE"
    provider.settings = Settings(mode="launchdarkly", sdk_key="sdk-test-only", flag_key="missing-flag")
    assert provider.evaluate(PROFILES[0], DemoState()).fallback


def test_live_api_cannot_override_flag_or_leak_key(sdk):
    """Only the incident simulation remains locally writable in live mode."""
    data, provider = sdk
    with TestClient(create_app(settings=provider.settings, features=provider)) as client:
        response = client.get("/api/experience", params={"profile_key": "qa-001"})
        assert response.json()["mode"] == "launchdarkly"
        assert "sdk-test-only" not in response.text
        assert "sdk-test-only" not in client.get("/api/health").text
        assert client.put("/api/demo/state", json={"release": "new", "incident": False}).status_code == 409
        assert client.put("/api/demo/state", json={"release": "targeted", "incident": True}).status_code == 200
        assert client.get("/api/experience", params={"profile_key": "qa-001"}).json()["incident"] is False
    assert provider.client is None


def test_thread_notifications_are_coalesced_and_cleaned_up():
    """Worker callbacks wake each browser safely, without accumulating redundant updates."""
    async def scenario():
        updates = LiveUpdates()
        updates.bind()
        with updates.subscribe() as queue:
            worker = Thread(target=lambda: [updates.notify() for count in range(5)])
            worker.start()
            worker.join()
            await asyncio.sleep(0)
            assert queue.qsize() == 1
            assert await queue.get() is True
        assert len(updates.subscribers) == 0
    asyncio.run(scenario())


def test_settings_hide_secrets_and_validate_mode(monkeypatch):
    """Validate configuration without serializing real credentials into test output."""
    monkeypatch.setenv("APP_MODE", "launchdarkly")
    monkeypatch.setenv("LD_SDK_KEY", "sdk-test-only")
    assert "sdk-test-only" not in repr(Settings.from_environment())
    monkeypatch.setenv("LD_SDK_KEY", "")
    with pytest.raises(ValueError, match="Set LD_SDK_KEY"):
        Settings.from_environment()
    monkeypatch.setenv("APP_MODE", "invalid")
    with pytest.raises(ValueError, match="APP_MODE"):
        Settings.from_environment()
