// Load browser instrumentation only when a live public ID is configured.
// Preview and the initial customer page do not need to download the recording plugins.
// DEMO START telemetry-loading: Load recording plugins only in configured live mode and dispose them on hot replacement.
let runtime;
let loading;
let disposed = false;

export const telemetry = {
  async identify(config, profile) {
    if (config.mode !== "launchdarkly" || !config.client_side_id)
      return "not_configured";
    loading ??= import("./telemetryClient").then(
      ({ createBrowserTelemetry }) => {
        runtime = createBrowserTelemetry();
        return runtime;
      },
    );
    const client = await loading;
    if (disposed) return "unavailable";
    const status = await client.identify(config, profile);
    if (disposed) {
      client.close();
      return "unavailable";
    }
    return status;
  },
  offer(experience, offerId, operation) {
    return runtime
      ? runtime.offer(experience, offerId, operation)
      : operation();
  },
  close() {
    disposed = true;
    runtime?.close();
  },
};

// Release singleton resources during a development hot replacement rather than creating duplicates.
if (import.meta.hot) import.meta.hot.dispose(() => telemetry.close());
// DEMO END telemetry-loading
