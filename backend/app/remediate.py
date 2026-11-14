"""Manual incident-response command; reads the trigger URL from local server settings.

From the repository root: PYTHONPATH=backend .venv/bin/python -m app.remediate
Add --check to validate configuration without invoking the trigger.
"""

import argparse
import logging

from .remediation import FlagTrigger, RemediationError
from .settings import Settings


# DEMO START remediation-cli: Offer a dry configuration check and an explicit manual remediation command.
def main():
    parser = argparse.ArgumentParser(description="Invoke the configured LaunchDarkly Generic OFF trigger.")
    parser.add_argument("--check", action="store_true", help="Validate local configuration without sending a request")
    options = parser.parse_args()
    # HTTP debug logging can reveal the secret URL. Keep this standalone command quiet.
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    try:
        settings = Settings.from_environment()
        if settings.mode != "launchdarkly":
            raise RemediationError("Set APP_MODE=launchdarkly before invoking the real flag trigger.")
        trigger = FlagTrigger(settings.flag_trigger_url)
        if options.check:
            print("Trigger configuration is present and valid. No request was sent.")
            return 0
        status = trigger.fire()
        print(f"Trigger accepted (HTTP {status}). Verify the flag is Off and the existing panel returns.")
        return 0
    except (ValueError, RemediationError) as error:
        print(str(error))
        return 1
# DEMO END remediation-cli


if __name__ == "__main__":
    raise SystemExit(main())
