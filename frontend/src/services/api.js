// Central HTTP boundary. Credentials remain in Python; callers receive readable, classified errors.
// DEMO START http-errors: Classify real service outages separately from the intentional offers incident.
export class ApiError extends Error {
  constructor(message, { code = "request_failed", status } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError(
      "The demo service is unavailable. Check that the Python backend is running, then try again.",
      { code: "network_unavailable" },
    );
  }

  let body;
  try {
    body = await response.json();
  } catch {
    // A development proxy may return an empty/HTML 500 response during a real outage.
    // Never show a browser parser exception or the remote response body to the customer.
    const message = response.ok
      ? "The demo service returned an unexpected response. Please try again."
      : "The demo service is unavailable. Check that the Python backend is running, then try again.";
    throw new ApiError(message, {
      code: "invalid_response",
      status: response.status,
    });
  }

  if (!response.ok) {
    // Only the explicit simulation marker from Python identifies the intentional demo failure.
    const simulated =
      response.status === 503 &&
      response.headers.get("X-Demo-Incident") === "offers";
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : "Please check your request and try again.";
    throw new ApiError(message, {
      code: simulated ? "simulated_offer_incident" : "request_failed",
      status: response.status,
    });
  }
  return body;
}

// Components use these application operations instead of calling provider SDKs directly.
export const api = {
  config: () => request("/config"),
  profiles: () => request("/profiles"),
  state: () => request("/demo/state"),
  update: (state) =>
    request("/demo/state", { method: "PUT", body: JSON.stringify(state) }),
  activity: () => request("/activity"),
  engage: (profile_key, offer_id) =>
    request("/engagement", {
      method: "POST",
      body: JSON.stringify({ profile_key, offer_id }),
    }),
  chat: (profile_key, message) =>
    request("/chat", {
      method: "POST",
      body: JSON.stringify({ profile_key, message }),
    }),
};
// DEMO END http-errors
