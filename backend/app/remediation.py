"""Invoke the preconfigured Generic OFF flag trigger without exposing its secret URL.

This adapter sends a webhook, not a feature-flag REST API update or an adaptive trigger.
Setup: https://launchdarkly.com/docs/home/releases/triggers-create
"""

from urllib.parse import urlsplit

import httpx


class RemediationError(Exception):
    """A safe error message that never includes the trigger URL or remote response body."""


# DEMO START flag-trigger: Validate and call the secret Generic OFF trigger without logging its URL.
class FlagTrigger:
    """Keep the bearer-like webhook URL server-side and send one deliberate request."""

    def __init__(self, url, transport=None):
        self._url = url.strip()
        self._transport = transport
        # This demo uses LaunchDarkly's default region. Reject arbitrary HTTP destinations.
        try:
            parsed = urlsplit(self._url)
            valid = (
                parsed.scheme == "https"
                and parsed.hostname == "app.launchdarkly.com"
                and parsed.port in {None, 443}
                and parsed.path.startswith("/webhook/triggers/")
                and len(parsed.path.removeprefix("/webhook/triggers/")) > 0
                and parsed.username is None
                and parsed.password is None
                and not parsed.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise RemediationError("Set LD_FLAG_TRIGGER_URL to your default-region LaunchDarkly Generic OFF trigger URL.")

    def fire(self):
        # No automatic retry or redirect: a timed-out request may already have disabled the flag.
        # eventName gives the flag's change history a customer-readable incident description.
        try:
            with httpx.Client(transport=self._transport, timeout=10, follow_redirects=False) as client:
                response = client.post(self._url, json={"eventName": "ABC Bank demo: simulated offers incident"})
        except httpx.HTTPError:
            raise RemediationError("Trigger request failed. Check the flag state before trying again; the request may have reached LaunchDarkly.") from None
        if not 200 <= response.status_code < 300:
            # Do not print the body: error responses can echo credential-bearing request URLs.
            raise RemediationError(f"Trigger returned HTTP {response.status_code}. Check its configuration and flag state in LaunchDarkly.")
        return response.status_code
# DEMO END flag-trigger
