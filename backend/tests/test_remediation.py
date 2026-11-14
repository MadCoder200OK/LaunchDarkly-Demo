"""Validate webhook behavior with an isolated transport; never invoke a real flag trigger."""

import httpx
import pytest

from app.remediation import FlagTrigger, RemediationError
from app.settings import Settings


TEST_URL = "https://app.launchdarkly.com/webhook/triggers/test-secret"


def test_trigger_posts_once_and_preserves_audit_context():
    """The incident command invokes the webhook directly, without SDK credentials."""
    requests = []

    def respond(request):
        requests.append(request)
        assert request.method == "POST"
        assert b"ABC Bank demo: simulated offers incident" in request.content
        assert "authorization" not in request.headers
        return httpx.Response(200)

    assert FlagTrigger(TEST_URL, httpx.MockTransport(respond)).fire() == 200
    assert len(requests) == 1
    assert "test-secret" not in repr(Settings(flag_trigger_url=TEST_URL))


@pytest.mark.parametrize("status", [302, 400, 401, 429, 500])
def test_remote_errors_are_sanitized_and_never_follow_redirects(status):
    """Neither echoed secrets nor redirect destinations should reach command output."""
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, text=TEST_URL, headers={"Location": "https://example.com"})

    with pytest.raises(RemediationError) as failure:
        FlagTrigger(TEST_URL, httpx.MockTransport(respond)).fire()
    assert str(status) in str(failure.value)
    assert "test-secret" not in str(failure.value)
    assert len(requests) == 1


def test_timeout_is_sanitized_and_not_retried():
    """A timeout does not establish that the remote flag remained unchanged."""
    def timeout(request):
        raise httpx.ReadTimeout(TEST_URL)

    with pytest.raises(RemediationError) as failure:
        FlagTrigger(TEST_URL, httpx.MockTransport(timeout)).fire()
    assert "test-secret" not in str(failure.value)
    assert "Check the flag state" in str(failure.value)


@pytest.mark.parametrize("url", ["", "http://app.launchdarkly.com/webhook/triggers/test", "https://example.com/webhook/triggers/test", "https://app.launchdarkly.com/api/v2/flags", "https://app.launchdarkly.com/webhook/triggers/", "https://user:secret@app.launchdarkly.com/webhook/triggers/test"])
def test_invalid_trigger_destinations_are_rejected(url):
    """A malformed local configuration must not cause requests to arbitrary endpoints."""
    with pytest.raises(RemediationError, match="LD_FLAG_TRIGGER_URL"):
        FlagTrigger(url)
