"""Business-event and public-configuration checks with injected adapters, never a real LD account."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.adapters import PreviewFeatures
from app.catalog import PROFILES
from app.events import LaunchDarklyEvents
from app.main import create_app
from app.settings import Settings


def test_event_adapter_reuses_context_and_queues_once():
    """Conversions use the same user identity as flag evaluation, without making another SDK client."""
    recorded = []
    client = SimpleNamespace(is_initialized=lambda: True, track=lambda *arguments: recorded.append(arguments))
    provider = SimpleNamespace(client=client, context=lambda profile: {'key': profile.key})
    assert LaunchDarklyEvents(provider).track('offer-click', PROFILES[0], {'offer_id': 'travel'})
    assert recorded == [('offer-click', {'key': 'qa-001'}, {'offer_id': 'travel'})]
    provider.client = None
    assert not LaunchDarklyEvents(provider).track('offer-click', PROFILES[0], {})


def test_offer_intent_and_error_events_are_separate_and_config_is_allowlisted():
    """A valid failed click counts as intent; invalid requests never become metric events."""
    class LiveFeatures(PreviewFeatures):
        mode = 'launchdarkly'

    class Recorder:
        def __init__(self):
            self.entries = []

        def track(self, key, profile, data):
            self.entries.append((key, profile.key, data))
            return True

    tracker = Recorder()
    settings = Settings(mode='launchdarkly', sdk_key='sdk-test-private', flag_trigger_url='private-trigger', client_side_id='public123')
    with TestClient(create_app(settings=settings, features=LiveFeatures(), events=tracker)) as client:
        config = client.get('/api/config')
        assert config.json()['client_side_id'] == 'public123'
        assert 'sdk-test-private' not in config.text and 'private-trigger' not in config.text
        payload = {'profile_key': 'qa-001', 'offer_id': 'travel'}
        assert client.post('/api/engagement', json=payload).json()['experiment_event'] == 'queued'
        client.put('/api/demo/state', json={'release': 'targeted', 'incident': True})
        assert client.post('/api/engagement', json=payload).status_code == 503
        assert [entry[0] for entry in tracker.entries] == ['offer-click', 'offer-click', 'offer-error']
        assert all(entry[1] == 'qa-001' for entry in tracker.entries)
        assert client.post('/api/engagement', json={**payload, 'offer_id': 'invalid'}).status_code == 404
        assert len(tracker.entries) == 3


def test_preview_does_not_send_experiment_events_or_expose_browser_credentials():
    """A local rehearsal cannot silently become trial account traffic."""
    with TestClient(create_app(settings=Settings(client_side_id='public123'))) as client:
        assert client.get('/api/config').json()['client_side_id'] == ''
        response = client.post('/api/engagement', json={'profile_key': 'qa-001', 'offer_id': 'travel'})
        assert response.json()['experiment_event'] == 'not_sent'
