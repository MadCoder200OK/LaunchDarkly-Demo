# Implementation map

Complete feature blocks, including their purpose and exact source boundaries. Links include the START and END comments. Paths are relative to the project root.

| Feature / purpose | Implementation |
| --- | --- |
| Prepare dependencies once and preserve the user's local credentials. | [dev.py · lines 73–108](../dev.py#L73-L108) |
| Stop only the two children this launcher owns, with a bounded wait. | [dev.py · lines 119–143](../dev.py#L119-L143) |
| Start Python and Vite together without touching existing IDE processes. | [dev.py · lines 170–229](../dev.py#L170-L229) |
| Provide credential-free preview targeting without sending cloud evaluations. | [backend/app/adapters.py · lines 9–33](../backend/app/adapters.py#L9-L33) |
| Keep a bounded local presenter feed separate from LaunchDarkly telemetry. | [backend/app/adapters.py · lines 36–44](../backend/app/adapters.py#L36-L44) |
| Return clearly scripted answers when live AI is disabled or unavailable. | [backend/app/adapters.py · lines 47–69](../backend/app/adapters.py#L47-L69) |
| Share feature evaluation with the separate AI SDK without transferring client ownership. | [backend/app/ai_assistant.py · lines 19–41](../backend/app/ai_assistant.py#L19-L41) |
| Initialize the separate AI SDK with shared feature evaluation and content capture disabled. | [backend/app/ai_assistant.py · lines 56–71](../backend/app/ai_assistant.py#L56-L71) |
| Preserve tokens and original invocation attribution when a provider response is rejected. | [backend/app/ai_assistant.py · lines 77–100](../backend/app/ai_assistant.py#L77-L100) |
| Evaluate the managed config on each independent question and return safe variation metadata. | [backend/app/ai_assistant.py · lines 102–137](../backend/app/ai_assistant.py#L102-L137) |
| Label scripted recovery separately from a successful paid model generation. | [backend/app/ai_assistant.py · lines 139–149](../backend/app/ai_assistant.py#L139-L149) |
| Close AI-owned resources without closing the borrowed feature client twice. | [backend/app/ai_assistant.py · lines 151–161](../backend/app/ai_assistant.py#L151-L161) |
| Evaluate managed prompts per request and record success, usage, errors, and labeled fallbacks. | [backend/app/ai_assistant.py · lines 44–162](../backend/app/ai_assistant.py#L44-L162) |
| Define stable fictional QA, Premium, Standard, and twenty experiment identities. | [backend/app/catalog.py · lines 7–20](../backend/app/catalog.py#L7-L20) |
| Queue conversion events with the same context used for flag evaluation. | [backend/app/events.py · lines 13–28](../backend/app/events.py#L13-L28) |
| Initialize one streaming Python SDK client per server process. | [backend/app/launchdarkly_features.py · lines 24–32](../backend/app/launchdarkly_features.py#L24-L32) |
| Re-evaluate open visitor views when the offers flag changes. | [backend/app/launchdarkly_features.py · lines 34–39](../backend/app/launchdarkly_features.py#L34-L39) |
| Publish SDK connectivity changes to open visitor views. | [backend/app/launchdarkly_features.py · lines 41–44](../backend/app/launchdarkly_features.py#L41-L44) |
| Build stable user contexts with the exact targeting attributes and types. | [backend/app/launchdarkly_features.py · lines 46–58](../backend/app/launchdarkly_features.py#L46-L58) |
| Evaluate the Boolean offers flag with a safe false fallback and a reason. | [backend/app/launchdarkly_features.py · lines 60–81](../backend/app/launchdarkly_features.py#L60-L81) |
| Distinguish initialized cached data from a currently connected SDK stream. | [backend/app/launchdarkly_features.py · lines 83–90](../backend/app/launchdarkly_features.py#L83-L90) |
| Remove listeners and close the shared feature SDK on shutdown. | [backend/app/launchdarkly_features.py · lines 92–101](../backend/app/launchdarkly_features.py#L92-L101) |
| Bridge SDK listener threads to bounded browser event queues and close open streams. | [backend/app/live_updates.py · lines 7–51](../backend/app/live_updates.py#L7-L51) |
| Start and close injected integrations once for the application lifetime. | [backend/app/main.py · lines 30–45](../backend/app/main.py#L30-L45) |
| Expose only public browser configuration and allowlisted integration status. | [backend/app/main.py · lines 69–74](../backend/app/main.py#L69-L74) |
| Change local incident simulation while keeping live release decisions in LaunchDarkly. | [backend/app/main.py · lines 84–94](../backend/app/main.py#L84-L94) |
| Push evaluated experience updates over SSE without reloading the page. | [backend/app/main.py · lines 96–121](../backend/app/main.py#L96-L121) |
| Track offer intent once and distinguish simulated incidents from service outages. | [backend/app/main.py · lines 127–149](../backend/app/main.py#L127-L149) |
| Validate the question and delegate to the isolated assistant integration. | [backend/app/main.py · lines 151–159](../backend/app/main.py#L151-L159) |
| Retain actual rejected-response usage without exposing the response content. | [backend/app/openai_provider.py · lines 15–23](../backend/app/openai_provider.py#L15-L23) |
| Call the managed OpenAI model with bounded output, no retries, and response validation. | [backend/app/openai_provider.py · lines 26–83](../backend/app/openai_provider.py#L26-L83) |
| Offer a dry configuration check and an explicit manual remediation command. | [backend/app/remediate.py · lines 14–36](../backend/app/remediate.py#L14-L36) |
| Validate and call the secret Generic OFF trigger without logging its URL. | [backend/app/remediation.py · lines 16–53](../backend/app/remediation.py#L16-L53) |
| Close long-lived SSE responses before the HTTP server drains requests. | [backend/app/run.py · lines 8–23](../backend/app/run.py#L8-L23) |
| Compose offers and incident behavior through SDK-independent service interfaces. | [backend/app/service.py · lines 8–23](../backend/app/service.py#L8-L23) |
| Load server credentials privately from the root .env and validate live mode. | [backend/app/settings.py · lines 10–52](../backend/app/settings.py#L10-L52) |
| Subscribe to evaluated server updates and refresh the displayed experience without reload. | [frontend/src/hooks/useExperience.js · lines 4–20](../frontend/src/hooks/useExperience.js#L4-L20) |
| Initialize public browser instrumentation and follow the selected fictional visitor. | [frontend/src/hooks/useTelemetry.js · lines 6–26](../frontend/src/hooks/useTelemetry.js#L6-L26) |
| Classify real service outages separately from the intentional offers incident. | [frontend/src/services/api.js · lines 2–77](../frontend/src/services/api.js#L2-L77) |
| Load recording plugins only in configured live mode and dispose them on hot replacement. | [frontend/src/services/telemetry.js · lines 3–40](../frontend/src/services/telemetry.js#L3-L40) |
| Compose the official browser SDK, Observability, and Session Replay plugins. | [frontend/src/services/telemetryClient.js · lines 7–16](../frontend/src/services/telemetryClient.js#L7-L16) |
| Match browser user identities and attribute types to Python evaluations. | [frontend/src/services/telemetryCore.js · lines 23–36](../frontend/src/services/telemetryCore.js#L23-L36) |
| Enable official recording plugins with strict replay masking and no bodies, headers, or console capture. | [frontend/src/services/telemetryCore.js · lines 51–70](../frontend/src/services/telemetryCore.js#L51-L70) |
| Serialize visitor identification before attributing browser telemetry. | [frontend/src/services/telemetryCore.js · lines 38–87](../frontend/src/services/telemetryCore.js#L38-L87) |
| Record a successful offer action with fictional visitor and variation attributes. | [frontend/src/services/telemetryCore.js · lines 112–116](../frontend/src/services/telemetryCore.js#L112-L116) |
| Record a handled failure and error log using fixed messages that exclude customer content. | [frontend/src/services/telemetryCore.js · lines 123–138](../frontend/src/services/telemetryCore.js#L123-L138) |
| Measure both successful and failed request duration as a histogram. | [frontend/src/services/telemetryCore.js · lines 141–149](../frontend/src/services/telemetryCore.js#L141-L149) |
| Wrap one customer action in a browser span and correlate its flag evaluation without duplicating the action. | [frontend/src/services/telemetryCore.js · lines 89–161](../frontend/src/services/telemetryCore.js#L89-L161) |
| Identify visitors, protect replay content, and correlate offer traces, errors, logs, and metrics. | [frontend/src/services/telemetryCore.js · lines 2–173](../frontend/src/services/telemetryCore.js#L2-L173) |
| Connect the customer journey, visitor selection, engagement, and accessible outcome dialogs. | [frontend/src/App.jsx · lines 20–221](../frontend/src/App.jsx#L20-L221) |
| Present independent AI questions, variation attribution, fallbacks, and scroll-aware replies. | [frontend/src/components/Assistant.jsx · lines 6–147](../frontend/src/components/Assistant.jsx#L6-L147) |
| Expose diagnostics, local incident simulation, and preview-only release controls. | [frontend/src/components/DemoPanel.jsx · lines 7–228](../frontend/src/components/DemoPanel.jsx#L7-L228) |
| Select stable eligible visitors without assigning their experiment treatment locally. | [frontend/src/components/ExperimentVisitors.jsx · lines 2–17](../frontend/src/components/ExperimentVisitors.jsx#L2-L17) |
| Render the existing or personalized offer panel from the server decision. | [frontend/src/components/Offers.jsx · lines 6–56](../frontend/src/components/Offers.jsx#L6-L56) |
| Show the selected offers experience above the fold. | [frontend/src/components/OffersHero.jsx · lines 4–94](../frontend/src/components/OffersHero.jsx#L4-L94) |
