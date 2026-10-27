"""
The MCP server `dominion` over stdio: Claude in the seat of a game, through a server of the game of its own or the
one named, docs/lab/players.md.
"""

import logging
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from functools import wraps
from pathlib import Path

import click
import httpx
from mcp.server.mcpserver import MCPServer

from ..client import Api, Refused, words
from ..core.settings import Settings
from .sitting import Sitting

NAME = 'dominion'
HOST = '127.0.0.1'
LOG = 'mcp-server.log'
STARTS_WITHIN_S = 30.0
POLL_S = 0.2
NOISY = ('httpx', 'httpcore', 'websockets')
RULES = """
You sit in the council of a band of foragers as one voice of it, weighed by your standing. The band does what the
council decides; you only speak at a council when it sits for you. Look, read the council, vote by a number, then
advance to the next council. A standing that falls to 0 turns you out; the goal is 150 people within about 18 years.
"""

type Tool = Callable[..., str]


def _spoken(sitting: Sitting, tool: Tool) -> Tool:
    """
    A refusal of the server is told in its words instead of failing the tool.
    """

    @wraps(tool)
    def spoken(*args: object, **kwargs: object) -> str:
        try:
            return tool(*args, **kwargs)
        except Refused as refused:
            return words({'key': refused.key, 'values': refused.values}, sitting.lang)

    return spoken


def server(sitting: Sitting) -> MCPServer:
    """
    The tools of the seat, each a method of the sitting; nothing the seat does not see.
    """
    found = MCPServer(NAME, instructions=RULES.strip())
    tools: dict[str, tuple[Tool, str]] = {
        'new_game': (
            sitting.new_game,
            'Start a new game in your seat, by seed and preset, in English (en) or Russian (ru); the game played '
            'before ends. Gives what the seat sees at the start.',
        ),
        'look': (
            sitting.look,
            'The date and your standing, the band, the map of the land it knows around it, whether a council '
            'sits, and what happened since the last look.',
        ),
        'council': (
            sitting.council,
            "The options of the council that sits, numbered: their places, votes and the band's score of each; "
            'abstaining after them, 0 for silence.',
        ),
        'vote': (
            sitting.vote,
            'Answer the council by the number of an option; 0 keeps silent. Gives what that answer led to.',
        ),
        'advance': (
            sitting.advance,
            'Let the band live until a council sits for you, or for the days given; gives what happened on the way.',
        ),
        'panes': (
            sitting.panes,
            'The people by stage, condition and role, every skill of the game with those learned marked +, and the '
            'stores and goods.',
        ),
        'end': (sitting.end, 'End the game; its record replays with make replay.'),
    }
    for name, (tool, description) in tools.items():
        found.add_tool(_spoken(sitting, tool), name=name, description=description, structured_output=False)
    return found


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        port: int = probe.getsockname()[1]
        return port


def _awaited(api: Api, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            api.health()
            return
        except httpx.TransportError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(POLL_S)


@contextmanager
def _own_server(data: Path) -> Iterator[str]:
    """
    A server of the game on a free port for as long as the MCP server, its log in the data directory.
    """
    data.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    command = [sys.executable, '-m', 'uvicorn', '--factory', 'dominion_theory.api:create_app']
    with (data / LOG).open('ab') as log:
        process = subprocess.Popen(  # noqa: S603
            [*command, '--host', HOST, '--port', str(port)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    try:
        yield f'http://{HOST}:{port}'
    finally:
        process.terminate()
        process.wait()


@click.command()
@click.option('--server', 'address', help='Play on this server instead of starting one.')
def cli(address: str | None) -> None:
    """
    Serve the seat of a game to an MCP client over stdio.
    """
    for name in NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)
    started = _own_server(Settings().data_dir) if address is None else _given(address)
    with started as found, closing(Api(found)) as api:
        _awaited(api, STARTS_WITHIN_S)
        server(Sitting(api)).run('stdio')


@contextmanager
def _given(address: str) -> Iterator[str]:
    yield address


if __name__ == '__main__':
    cli()
