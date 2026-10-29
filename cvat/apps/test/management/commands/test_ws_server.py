"""
WebSocket server that notifies browsers when a task's annotations change.

Run as a management command in a dedicated container (see
docker-compose.override.yml). It subscribes to the Redis pub/sub channel
PUBLISH_CHANNEL, where Django publishes a task id after every annotation save
(see cvat/apps/test/signals.py), and forwards the message to every client
connected at /ws/<task_id>.

The socket deliberately carries no annotation data: clients re-fetch the
counts through the authenticated HTTP API when notified. This keeps
authorization in one place (the API endpoint) and the WebSocket service
stateless with respect to CVAT users.
"""

import asyncio
import logging
import os

import redis.asyncio as aioredis
from django.conf import settings
from django.core.management.base import BaseCommand
from websockets.asyncio.server import ServerConnection, serve

from cvat.apps.test.signals import PUBLISH_CHANNEL

logger = logging.getLogger("cvat.apps.test")

# task_id -> set of open connections
connections: dict[int, set[ServerConnection]] = {}


class Command(BaseCommand):
    help = "Run the WebSocket server broadcasting annotation updates per task"

    def add_arguments(self, parser):
        parser.add_argument("--host", default=os.getenv("TEST_WS_HOST", "0.0.0.0"))
        parser.add_argument("--port", type=int, default=int(os.getenv("TEST_WS_PORT", "8090")))

    def handle(self, *args, **options):
        asyncio.run(self.serve(options["host"], options["port"]))

    async def serve(self, host: str, port: int) -> None:
        password = settings.REDIS_INMEM_SETTINGS["PASSWORD"]
        auth = f":{password}@" if password else ""
        redis_url = (
            f"redis://{auth}{settings.REDIS_INMEM_SETTINGS['HOST']}:"
            f"{settings.REDIS_INMEM_SETTINGS['PORT']}/0"
        )
        client = aioredis.from_url(redis_url)
        pubsub = client.pubsub()
        await pubsub.subscribe(PUBLISH_CHANNEL)
        self.stdout.write(
            f"test_ws_server listening on ws://{host}:{port}, "
            f"subscribed to {PUBLISH_CHANNEL}"
        )

        async def broadcast() -> None:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                task_id = int(message["data"])
                for conn in list(connections.get(task_id, ())):
                    try:
                        await conn.send(message["data"].decode())
                    except Exception:
                        pass

        async with serve(self.handler, host, port):
            await broadcast()

    async def handler(self, connection: ServerConnection) -> None:
        # Expected path: /ws/<task_id>
        raw = connection.request.path.strip("/").split("/")
        if len(raw) != 2 or raw[0] != "ws" or not raw[1].isdigit():
            await connection.close(code=4000, reason="expected /ws/<task_id>")
            return

        task_id = int(raw[1])
        connections.setdefault(task_id, set()).add(connection)
        try:
            await connection.wait_closed()
        finally:
            conns = connections.get(task_id)
            if conns is not None:
                conns.discard(connection)
                if not conns:
                    connections.pop(task_id, None)
