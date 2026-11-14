// Provider boundary: injected SDK dependencies keep instrumentation testable without a browser.
// DEMO START browser-telemetry: Identify visitors, protect replay content, and correlate offer traces, errors, logs, and metrics.
export function createTelemetry({
  sdk,
  observe,
  Observability,
  SessionReplay,
}) {
  let client;
  let currentProfile;
  let ready = false;
  let pending = Promise.resolve();

  function safely(action) {
    // Diagnostics must not change the success or failure of a customer's offer action.
    try {
      return action();
    } catch {
      return undefined;
    }
  }

  // DEMO START browser-context: Match browser user identities and attribute types to Python evaluations.
  function context(profile) {
    // Keep context keys and targeting attribute types identical to the Python SDK.
    return {
      kind: "user",
      key: profile.key,
      name: profile.name,
      tier: profile.tier,
      geography: profile.geography,
      beta_tester: profile.beta_tester,
      experiment_eligible: profile.experiment_eligible,
    };
  }
  // DEMO END browser-context

  // DEMO START browser-identify: Serialize visitor identification before attributing browser telemetry.
  function identify(config, profile) {
    // Serialize identify calls so rapid profile switching cannot attach telemetry to an old user.
    pending = pending
      .catch(() => {})
      .then(async () => {
        ready = false;
        currentProfile = undefined;
        if (config.mode !== "launchdarkly" || !config.client_side_id)
          return "not_configured";
        if (!client) {
          client = sdk.initialize(config.client_side_id, context(profile), {
            streaming: true,
            // DEMO START browser-privacy: Enable official recording plugins with strict replay masking and no bodies, headers, or console capture.
            plugins: [
              new Observability({
                disableConsoleRecording: true,
                networkRecording: {
                  enabled: true,
                  recordHeadersAndBody: false,
                },
              }),
              new SessionReplay({
                privacySetting: "strict",
                blockSelector: "[data-private]",
                disableConsoleRecording: true,
                networkRecording: {
                  enabled: true,
                  recordHeadersAndBody: false,
                },
              }),
            ],
            // DEMO END browser-privacy
          });
          await client.waitForInitialization(5);
        } else {
          await client.identify(context(profile));
        }
        currentProfile = profile.key;
        ready = true;
        safely(() =>
          observe.recordLog("ABC Bank demo visitor selected", "info", {
            "demo.profile": profile.key,
          }),
        );
        return "ready";
      });
    return pending;
  }
  // DEMO END browser-identify

  // DEMO START offer-trace: Wrap one customer action in a browser span and correlate its flag evaluation without duplicating the action.
  async function offer(experience, offerId, operation) {
    if (!ready || currentProfile !== experience.profile.key) return operation();
    const attributes = {
      "demo.offer": offerId,
      "demo.variant": experience.decision.variant,
      "demo.profile": experience.profile.key,
      "demo.simulated_incident": experience.incident,
    };
    let operationPromise;
    const run = (span) => {
      // A tracer may fail after its callback, replace its return value, or call it twice.
      // Keep one authoritative customer-operation promise independent of that wrapper.
      if (operationPromise) return operationPromise;
      const began = performance.now();
      // Evaluate synchronously while the tracer's callback context is active. Browser context
      // managers need not carry that active span into a later promise/microtask.
      // Python remains authoritative for rendering and emits the experiment conversion once.
      safely(() => client.variation(experience.integration.flag_key, false));
      safely(() => span?.setAttributes(attributes));
      operationPromise = Promise.resolve().then(async () => {
        try {
          const result = await operation();
          // DEMO START offer-log: Record a successful offer action with fictional visitor and variation attributes.
          safely(() =>
            observe.recordLog("ABC Bank offer explored", "info", attributes),
          );
          // DEMO END offer-log
          return result;
        } catch (error) {
          safely(() =>
            span?.setStatus({ code: 2, message: "Offer request failed" }),
          );
          // Only a fixed diagnostic message is recorded; questions and response bodies are omitted.
          // DEMO START offer-error: Record a handled failure and error log using fixed messages that exclude customer content.
          safely(() =>
            observe.recordError(
              new Error("ABC Bank offer request failed"),
              "Offers panel request failed",
              attributes,
            ),
          );
          safely(() =>
            observe.recordLog(
              "ABC Bank offer request failed",
              "error",
              attributes,
            ),
          );
          // DEMO END offer-error
          throw error;
        } finally {
          // DEMO START offer-duration: Measure both successful and failed request duration as a histogram.
          safely(() =>
            observe.recordHistogram({
              name: "abc.offer.request.duration_ms",
              value: performance.now() - began,
              attributes,
            }),
          );
          // DEMO END offer-duration
        }
      });
      return operationPromise;
    };
    try {
      await observe.startSpan("abc.offer.explore", run);
    } catch {
      // The operation's own promise preserves real failures as well as successful responses.
    }
    return operationPromise ?? run();
  }
  // DEMO END offer-trace

  return {
    identify,
    offer,
    close: () => {
      ready = false;
      client?.close();
      client = undefined;
    },
  };
}
// DEMO END browser-telemetry
