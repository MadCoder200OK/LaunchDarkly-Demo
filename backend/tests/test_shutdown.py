"""Exercise real HTTP streaming and server shutdown without real keys or TCP ports."""

import asyncio
import socket
from tempfile import TemporaryDirectory

import httpx

from app.adapters import PreviewFeatures
from app.main import create_app
from app.run import DemoServer
from app.settings import Settings


def test_shutdown_finishes_with_open_stream_and_cleans_up_sdk():
    """An idle browser connection must end without waiting for its next 15-second heartbeat."""
    class Features(PreviewFeatures):
        closed = False

        def close(self):
            self.closed = True

    async def scenario(path):
        features = Features()
        app = create_app(settings=Settings(), features=features)
        server = DemoServer(app, log_level='error')
        # Unix-domain HTTP exercises Uvicorn's real connection draining without using port 8000.
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(path)
        listener.listen()
        listener.setblocking(False)
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            async with asyncio.timeout(5):
                while not server.started:
                    if task.done():
                        await task
                        raise AssertionError('Test server exited before startup')
                    await asyncio.sleep(0.01)
            transport = httpx.AsyncHTTPTransport(uds=path)
            async with httpx.AsyncClient(transport=transport, base_url='http://demo') as client:
                async with client.stream('GET', '/api/stream', params={'profile_key': 'experiment-001'}) as response:
                    lines = response.aiter_lines()
                    assert (await anext(lines)).startswith('data: ')
                    assert len(app.state.live_updates.subscribers) == 1
                    # Also cover shutdown taking priority over an already queued update.
                    app.state.live_updates.notify()
                    server.should_exit = True
                    # Below the 3-second cancellation fallback: the stream must end naturally.
                    await asyncio.wait_for(task, timeout=2)
                    assert not server.server_state.tasks
                    assert not app.state.live_updates.subscribers
                    assert features.closed
                    assert not app.state.live_updates.loop.is_closed()
        finally:
            server.should_exit = True
            if not task.done():
                await asyncio.wait_for(task, timeout=5)
            listener.close()

    # macOS Unix socket paths are short; pytest's default temp directory can exceed the limit.
    with TemporaryDirectory(dir='/tmp', prefix='abc-') as directory:
        asyncio.run(scenario(directory + '/api.sock'))
