// This dynamically loaded module is the only browser SDK/plugin composition point.
import * as sdk from "launchdarkly-js-client-sdk";
import Observability, { LDObserve } from "@launchdarkly/observability";
import SessionReplay from "@launchdarkly/session-replay";
import { createTelemetry } from "./telemetryCore";

// DEMO START browser-sdk: Compose the official browser SDK, Observability, and Session Replay plugins.
export function createBrowserTelemetry() {
  return createTelemetry({
    sdk,
    observe: LDObserve,
    Observability,
    SessionReplay,
  });
}
// DEMO END browser-sdk
