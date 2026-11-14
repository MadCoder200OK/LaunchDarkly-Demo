// HTTP failure classification regressions; these mocks never contact the demo or provider accounts.
import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiError, request } from "./api.js";

test("network failures have a readable message without leaking the raw exception", async (t) => {
  t.mock.method(globalThis, "fetch", async () => {
    throw Error("private proxy diagnostic");
  });
  await assert.rejects(request("/engagement"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.code, "network_unavailable");
    assert.match(error.message, /Python backend/);
    assert.doesNotMatch(error.message, /private proxy/);
    return true;
  });
});

test("empty and HTML HTTP errors never expose JSON parser errors or response bodies", async (t) => {
  for (const content of ["", "<html>private proxy diagnostic</html>"]) {
    const mock = t.mock.method(
      globalThis,
      "fetch",
      async () => new Response(content, { status: 500 }),
    );
    await assert.rejects(request("/engagement"), (error) => {
      assert.equal(error.code, "invalid_response");
      assert.equal(error.status, 500);
      assert.match(error.message, /service is unavailable/);
      assert.doesNotMatch(error.message, /JSON|private proxy/);
      return true;
    });
    mock.mock.restore();
  }
});

test("only a marked 503 is a simulated incident", async (t) => {
  for (const [status, marker, expected] of [
    [503, "offers", "simulated_offer_incident"],
    [503, "", "request_failed"],
    [500, "offers", "request_failed"],
  ]) {
    const mock = t.mock.method(globalThis, "fetch", async () =>
      Response.json(
        { detail: "A safe server error" },
        { status, headers: { "X-Demo-Incident": marker } },
      ),
    );
    await assert.rejects(
      request("/engagement"),
      (error) =>
        error.code === expected && error.message === "A safe server error",
    );
    mock.mock.restore();
  }
});

test("invalid successful responses are classified and valid JSON is returned unchanged", async (t) => {
  const mock = t.mock.method(
    globalThis,
    "fetch",
    async () => new Response("not JSON"),
  );
  await assert.rejects(
    request("/profiles"),
    (error) =>
      error.code === "invalid_response" &&
      /unexpected response/.test(error.message),
  );
  mock.mock.restore();
  t.mock.method(globalThis, "fetch", async () =>
    Response.json({ status: "ok" }),
  );
  assert.deepEqual(await request("/health"), { status: "ok" });
});
