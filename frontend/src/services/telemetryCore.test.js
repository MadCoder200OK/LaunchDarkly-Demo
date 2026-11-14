// Node's built-in tests verify failure isolation and prevent duplicate customer actions.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createTelemetry } from "./telemetryCore.js";

function fixture({ tracerFails = false, wrapSpan } = {}) {
  const recorded = [];
  const client = {
    waitForInitialization: async () => {},
    identify: async (context) => recorded.push(context.key),
    variation: () => true,
    close: () => {},
  };
  const observe = {
    recordLog: (...values) => recorded.push(values),
    recordError: (...values) => recorded.push(values),
    recordHistogram: (metric) => recorded.push(metric),
    startSpan: async (name, callback) => {
      if (tracerFails) throw Error("tracer failed");
      const run = () => callback({ setAttributes() {}, setStatus() {} });
      return wrapSpan ? wrapSpan(run) : run();
    },
  };
  const dependencies = {
    sdk: { initialize: () => client },
    observe,
    Observability: class {},
    SessionReplay: class {},
  };
  const telemetry = createTelemetry(dependencies);
  const profile = {
    key: "qa-001",
    tier: "Standard",
    beta_tester: true,
    experiment_eligible: false,
  };
  const view = {
    profile,
    decision: { variant: "new" },
    integration: { flag_key: "personalized-offers" },
    incident: false,
  };
  return { telemetry, recorded, profile, view, client };
}

test("missing config leaves customer action functional without telemetry", async () => {
  const { telemetry, profile, view } = fixture();
  assert.equal(
    await telemetry.identify({ mode: "preview" }, profile),
    "not_configured",
  );
  assert.equal(await telemetry.offer(view, "travel", async () => "ok"), "ok");
});

test("successful and failed actions are each executed once", async () => {
  const { telemetry, profile, view, recorded } = fixture();
  await telemetry.identify(
    { mode: "launchdarkly", client_side_id: "public123" },
    profile,
  );
  let count = 0;
  assert.equal(
    await telemetry.offer(view, "travel", async () => {
      count += 1;
      return "ok";
    }),
    "ok",
  );
  await assert.rejects(
    telemetry.offer(view, "travel", async () => {
      count += 1;
      throw Error("private-response");
    }),
  );
  assert.equal(count, 2);
  assert.equal(
    recorded.filter((entry) => entry?.name === "abc.offer.request.duration_ms")
      .length,
    2,
  );
  assert.equal(JSON.stringify(recorded).includes("private-response"), false);
});

test("a broken tracer cannot suppress or duplicate the offer request", async () => {
  const { telemetry, profile, view } = fixture({ tracerFails: true });
  await telemetry.identify(
    { mode: "launchdarkly", client_side_id: "public123" },
    profile,
  );
  let count = 0;
  assert.equal(
    await telemetry.offer(view, "travel", async () => {
      count += 1;
      return "ok";
    }),
    "ok",
  );
  assert.equal(count, 1);
});

test("rapid visitor changes are serialized before attributing requests", async () => {
  const { telemetry, profile, view, recorded } = fixture();
  const config = { mode: "launchdarkly", client_side_id: "public123" };
  await Promise.all([
    telemetry.identify(config, profile),
    telemetry.identify(config, { ...profile, key: "standard-001" }),
  ]);
  const previous = recorded.length;
  await telemetry.offer(view, "travel", async () => "ok");
  assert.equal(recorded.length, previous);
});

test("tracer cleanup cannot replace a successful customer result or retry the request", async () => {
  const { telemetry, profile, view } = fixture({
    wrapSpan: async (run) => {
      await run();
      throw Error("tracer cleanup failed");
    },
  });
  await telemetry.identify(
    { mode: "launchdarkly", client_side_id: "public123" },
    profile,
  );
  let count = 0;
  assert.equal(
    await telemetry.offer(view, "travel", async () => {
      count++;
      return "customer-success";
    }),
    "customer-success",
  );
  assert.equal(count, 1);
});

test("the original offer error survives a different tracer cleanup failure", async () => {
  const original = Error("customer-operation-failed");
  const { telemetry, profile, view } = fixture({
    wrapSpan: async (run) => {
      try {
        await run();
      } finally {
        throw Error("tracer cleanup failed");
      }
    },
  });
  await telemetry.identify(
    { mode: "launchdarkly", client_side_id: "public123" },
    profile,
  );
  let count = 0;
  await assert.rejects(
    telemetry.offer(view, "travel", async () => {
      count++;
      throw original;
    }),
    (error) => error === original,
  );
  assert.equal(count, 1);
});

test("a tracer cannot duplicate an operation or replace its returned value", async () => {
  const { telemetry, profile, view } = fixture({
    wrapSpan: async (run) => {
      await Promise.all([run(), run()]);
      return "tracer-result";
    },
  });
  await telemetry.identify(
    { mode: "launchdarkly", client_side_id: "public123" },
    profile,
  );
  let count = 0;
  assert.equal(
    await telemetry.offer(view, "travel", async () => {
      count++;
      return "customer-success";
    }),
    "customer-success",
  );
  assert.equal(count, 1);
});

test("flag evaluation remains inside the synchronous trace callback context", async () => {
  let active = false;
  const { telemetry, profile, view, client } = fixture({
    wrapSpan: (run) => {
      active = true;
      try {
        return run();
      } finally {
        active = false;
      }
    },
  });
  let evaluations = 0;
  client.variation = () => {
    assert.equal(active, true);
    evaluations++;
    return true;
  };
  await telemetry.identify(
    { mode: "launchdarkly", client_side_id: "public123" },
    profile,
  );
  assert.equal(await telemetry.offer(view, "travel", async () => "ok"), "ok");
  assert.equal(evaluations, 1);
});
