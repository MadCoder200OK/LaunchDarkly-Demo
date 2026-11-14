"""Bridge SDK worker-thread notifications to asynchronous browser event streams."""

import asyncio
from contextlib import contextmanager


# DEMO START stream-bridge: Bridge SDK listener threads to bounded browser event queues and close open streams.
class LiveUpdates:
    def __init__(self):
        self.loop = None
        self.subscribers = set()
        self.closing = False

    def bind(self):
        self.loop = asyncio.get_running_loop()
        self.closing = False

    def notify(self):
        # SDK callbacks can run outside FastAPI's event loop; never write its queues directly.
        if not self.closing and self.loop is not None and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._publish)

    def _publish(self):
        # One pending notification is enough: subscribers always evaluate the latest state.
        if self.closing:
            return
        for subscriber in tuple(self.subscribers):
            if not subscriber.full():
                subscriber.put_nowait(True)

    def close(self):
        """Run on the app's event loop before the server waits for open requests."""
        self.closing = True
        for subscriber in tuple(self.subscribers):
            # Shutdown takes priority over a pending flag change in the bounded queue.
            if subscriber.full():
                subscriber.get_nowait()
            subscriber.put_nowait(None)

    @contextmanager
    def subscribe(self):
        # Each browser has its own queue, removed reliably when its stream disconnects.
        queue = asyncio.Queue(maxsize=1)
        self.subscribers.add(queue)
        if self.closing:
            queue.put_nowait(None)
        try:
            yield queue
        finally:
            self.subscribers.discard(queue)
# DEMO END stream-bridge
