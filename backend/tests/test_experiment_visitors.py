"""Cohort identity and attribution checks; never send test traffic to LaunchDarkly."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def test_cohort_revisits_preserve_identity_and_click_attribution():
    """All advertised demo users must resolve, stay outside Premium/QA, and track independently."""
    class Recorder:
        def __init__(self):
            self.keys = []

        def track(self, key, profile, data):
            self.keys.append((key, profile.key))
            return True

    tracker = Recorder()
    with TestClient(create_app(settings=Settings(), events=tracker)) as client:
        profiles = client.get('/api/profiles').json()
        visitors = [profile for profile in profiles if profile['experiment_eligible']]
        keys = [profile['key'] for profile in visitors]
        assert len(keys) >= 2 and len(keys) == len(set(keys))
        assert not set(keys) & {'qa-001', 'premium-001', 'standard-001'}
        assert visitors[0]['key'] == 'experiment-001' and visitors[0]['name'] == 'Jordan Lee'
        for profile in visitors:
            assert profile['tier'] == 'Standard' and profile['beta_tester'] is False
            view = client.get('/api/experience', params={'profile_key': profile['key']}).json()
            assert view['profile'] == profile
            assert view['decision']['variant'] == 'existing'  # Preview must not invent A/B assignments.
        for key in [keys[0], keys[1], keys[0]]:
            view = client.get('/api/experience', params={'profile_key': key}).json()
            assert view['profile']['key'] == key
            assert client.post('/api/engagement', json={'profile_key': key, 'offer_id': 'travel'}).status_code == 200
        assert tracker.keys == [('offer-click', keys[0]), ('offer-click', keys[1]), ('offer-click', keys[0])]
        assert client.get('/api/profiles').json() == profiles
