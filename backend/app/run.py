"""IDE/CLI entry point: close long-lived browser streams before draining HTTP requests."""

import argparse

import uvicorn


# DEMO START stream-shutdown: Close long-lived SSE responses before the HTTP server drains requests.
class DemoServer(uvicorn.Server):
    """Small adapter for the pinned Uvicorn version; SDK cleanup stays in app lifespan."""

    def __init__(self, app, **options):
        self.demo_app = app
        # A timeout bounds request draining if another request fails to finish normally.
        # It does not bound LD network cleanup or guarantee delivery of pending analytics.
        options.setdefault('timeout_graceful_shutdown', 3)
        super().__init__(uvicorn.Config(app, **options))

    async def shutdown(self, sockets=None):
        # Uvicorn drains requests BEFORE lifespan.shutdown; wake every SSE waiter first.
        self.demo_app.state.live_updates.close()
        await super().shutdown(sockets=sockets)
# DEMO END stream-shutdown


def main():
    parser = argparse.ArgumentParser(description='Run the local ABC Bank API with stream-aware shutdown')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    arguments = parser.parse_args()
    # Import only when launching so tests can inject a preview app without loading real SDKs.
    from .main import app

    try:
        DemoServer(app, host=arguments.host, port=arguments.port).run()
    except KeyboardInterrupt:
        # Uvicorn has already run its signal/lifespan cleanup; a normal Ctrl+C is not an app error.
        pass


if __name__ == '__main__':
    main()
