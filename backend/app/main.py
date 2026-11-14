"""HTTP routes and SDK lifecycle; customer-facing components consume this stable API."""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from .adapters import LocalActivity, PreviewAssistant, PreviewFeatures
from .catalog import OFFERS, PROFILES
from .domain import ChatRequest, DemoState, Engagement
from .service import DemoService
from .launchdarkly_features import LaunchDarklyFeatures
from .live_updates import LiveUpdates
from .settings import Settings
from .events import LaunchDarklyEvents, PreviewEvents
from .ai_assistant import LaunchDarklyAssistant


def create_app(settings=None, features=None, events=None, assistant=None):
    # Dependency injection lets tests use isolated preview or SDK test-data adapters.
    settings = settings or Settings.from_environment()
    features = features or (LaunchDarklyFeatures(settings) if settings.mode == "launchdarkly" else PreviewFeatures())
    events = events or (LaunchDarklyEvents(features) if features.mode == "launchdarkly" else PreviewEvents())
    updates = LiveUpdates()
    assistant = assistant or (LaunchDarklyAssistant(settings, features) if settings.ai_enabled and features.mode == 'launchdarkly' else PreviewAssistant())

    # DEMO START app-lifecycle: Start and close injected integrations once for the application lifetime.
    @asynccontextmanager
    async def lifespan(app):
        # Initialize once on startup, outside the event loop, and close on every shutdown path.
        updates.bind()
        try:
            await asyncio.to_thread(features.start, updates.notify)
            await assistant.start()
            yield
        finally:
            updates.close()
            try:
                await assistant.close()
            finally:
                await asyncio.to_thread(features.close)
    # DEMO END app-lifecycle

    app = FastAPI(title="ABC Bank demo API", version="0.2.0", lifespan=lifespan)
    # The server runner closes streams before Uvicorn waits for requests to finish.
    # Lifespan cleanup alone happens too late to unblock an indefinitely open SSE request.
    app.state.live_updates = updates
    activity = LocalActivity()
    service = DemoService(features, activity, assistant)

    def require_profile(key):
        profile = service.profile(key)
        if profile is None:
            raise HTTPException(404, "Unknown demo profile")
        return profile

    @app.get("/api/health")
    async def health():
        status = features.status()
        return {"status": "ok", "mode": features.mode, "launchdarkly_connected": status["connected"], "integration": status}

    @app.get("/api/profiles")
    async def profiles():
        return PROFILES

    # DEMO START public-config: Expose only public browser configuration and allowlisted integration status.
    @app.get("/api/config")
    async def browser_config():
        # Explicit allowlist: never serialize Settings, which also contains two server secrets.
        return {"mode": features.mode, "client_side_id": settings.client_side_id if features.mode == "launchdarkly" else "", "flag_key": settings.flag_key, "trigger_configured": bool(settings.flag_trigger_url), "ai": assistant.status()}
    # DEMO END public-config

    @app.get("/api/experience")
    async def experience(profile_key: str):
        return service.view(require_profile(profile_key))

    @app.get("/api/demo/state")
    async def state():
        return service.state

    # DEMO START incident-controls: Change local incident simulation while keeping live release decisions in LaunchDarkly.
    @app.put("/api/demo/state")
    async def update_state(state: DemoState):
        # Real releases are controlled in LD. Only incident simulation remains a local control.
        if features.mode == "launchdarkly" and state.release != service.state.release:
            raise HTTPException(409, "Change release and targeting in LaunchDarkly, not the local preview controls")
        service.state = state
        activity.record("preview.updated", release=state.release, incident=str(state.incident))
        updates.notify()
        return state
    # DEMO END incident-controls

    # DEMO START sse-api: Push evaluated experience updates over SSE without reloading the page.
    @app.get("/api/stream")
    async def stream(request: Request, profile_key: str):
        if updates.closing:
            raise HTTPException(503, "Demo server is shutting down")
        profile = require_profile(profile_key)

        async def events():
            # Send the initial view, then push listener updates without requiring a page reload.
            with updates.subscribe() as queue:
                if updates.closing:
                    return
                yield "data: " + json.dumps(jsonable_encoder(service.view(profile))) + "\n\n"
                while not await request.is_disconnected():
                    try:
                        notification = await asyncio.wait_for(queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        # Keep the connection alive without generating extra flag evaluations.
                        yield ": heartbeat\n\n"
                        continue
                    if notification is None:
                        return  # End the HTTP response so normal server shutdown can proceed.
                    yield "data: " + json.dumps(jsonable_encoder(service.view(profile))) + "\n\n"

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    # DEMO END sse-api

    @app.get("/api/activity")
    async def recent_activity():
        return list(activity.entries)

    # DEMO START engagement: Track offer intent once and distinguish simulated incidents from service outages.
    @app.post("/api/engagement")
    async def engagement(event: Engagement):
        # A simulated failure returns a real 503; the local feed is not LD observability telemetry.
        profile = require_profile(event.profile_key)
        if event.offer_id not in {offer.id for offer in OFFERS}:
            raise HTTPException(404, "Unknown offer")
        view = service.view(profile)
        # A click is intent, even if the offers service fails. Track failures separately.
        metric_data = {"offer_id": event.offer_id, "variant": view["decision"].variant, "demo": True}
        queued = events.track("offer-click", profile, metric_data)
        if view["incident"]:
            events.track("offer-error", profile, metric_data)
            activity.record("offer.simulated_error", profile=profile.key, offer=event.offer_id)
            # Distinguish the intentional simulation from real proxy/network outages.
            raise HTTPException(
                503,
                "Simulated offers service issue. Restore the existing experience using LaunchDarkly in live mode or preview controls locally.",
                headers={"X-Demo-Incident": "offers"},
            )
        activity.record("offer.clicked", profile=profile.key, offer=event.offer_id, variant=view["decision"].variant)
        return {"message": "You're on the list. This is a demo confirmation; no application has been submitted.", "experiment_event": "queued" if queued else "not_sent"}
    # DEMO END engagement

    # DEMO START chat-api: Validate the question and delegate to the isolated assistant integration.
    @app.post("/api/chat")
    async def chat(request: ChatRequest):
        # Only the selected fictional identity and question reach the server; keys stay in Settings.
        profile = require_profile(request.profile_key)
        if not request.message.strip():
            raise HTTPException(422, "Enter a question")
        return await service.assistant.respond(request.message, profile)
    # DEMO END chat-api

    return app


app = create_app()
