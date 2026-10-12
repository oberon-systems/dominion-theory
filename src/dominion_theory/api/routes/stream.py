"""
The stream of updates: what was missed, then every update as the runner hands it out.
"""

import asyncio
from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ...core.errors import DominionError
from ...runner import Ended, Resync, Update
from ..context import Ctx
from ..errors import body_of, status_of
from ..schemas import View

# An error closes the stream with its HTTP status above this base, after its message.
CLOSE_BASE = 4000

router = APIRouter()


async def _until_gone(socket: WebSocket) -> None:
    with suppress(WebSocketDisconnect):
        while True:
            await socket.receive_text()


@router.websocket('/games/{game_id}/updates')
async def updates(
    socket: WebSocket,
    game_id: str,
    context: Ctx,
    after: Annotated[int | None, Query(ge=0)] = None,
    view: Annotated[View, Query()] = View.SEAT,
) -> None:
    await socket.accept()
    try:
        context.check_view(view)
        runner = context.runner(game_id)
    except DominionError as error:
        await socket.send_json(body_of(error))
        await socket.close(CLOSE_BASE + status_of(error))
        return
    queue: asyncio.Queue[Update | Ended] = asyncio.Queue()
    missed = runner.since(runner.seq if after is None else after)
    leave = runner.subscribe(queue.put_nowait)
    gone = asyncio.create_task(_until_gone(socket))
    try:
        for message in [missed] if isinstance(missed, Resync) else missed:
            await socket.send_json(message.data())
        while True:
            ready = asyncio.create_task(queue.get())
            await asyncio.wait({ready, gone}, return_when=asyncio.FIRST_COMPLETED)
            if not ready.done():
                ready.cancel()
                return
            heard = ready.result()
            if isinstance(heard, Ended):
                await socket.close()
                return
            await socket.send_json(heard.data())
    except WebSocketDisconnect:
        return
    finally:
        leave()
        gone.cancel()
