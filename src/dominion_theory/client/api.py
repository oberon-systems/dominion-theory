"""
The API as a client reaches it: requests over HTTP, the stream of updates over a WebSocket.
"""

import json
from collections.abc import Generator
from typing import Any

import httpx
from websockets.sync.client import connect

PREFIX = '/api/v1'
SERVER = 'http://127.0.0.1:8000'
TIMEOUT = 30.0

type Body = dict[str, Any]


class Refused(Exception):
    """
    An answer that is a message of the server: a key with values, as the protocol states errors.
    """

    def __init__(self, key: str, values: Body) -> None:
        super().__init__(key)
        self.key = key
        self.values = values


def _refusal(message: Any) -> Refused | None:
    if isinstance(message, dict) and isinstance(message.get('key'), str):
        return Refused(message['key'], dict(message.get('values') or {}))
    return None


class Api:
    def __init__(self, server: str = SERVER) -> None:
        self._base = server.rstrip('/') + PREFIX
        self._http = httpx.Client(base_url=self._base, timeout=TIMEOUT)

    def close(self) -> None:
        self._http.close()

    def language(self) -> str:
        return str(self._read('GET', '/profile')['language'])

    def create(
        self,
        mode: str,
        seed: int | None = None,
        preset: str | None = None,
        overrides: Body | None = None,
    ) -> Body:
        asked = {'mode': mode, 'seed': seed, 'preset': preset, 'overrides': overrides or None}
        return self._read('POST', '/games', {name: value for name, value in asked.items() if value is not None})

    def game(self, game_id: str) -> Body:
        return self._read('GET', f'/games/{game_id}')

    def snapshot(self, game_id: str) -> Body:
        return self._read('GET', f'/games/{game_id}/snapshot')

    def clock(self, game_id: str, action: str) -> Body:
        return self._read('POST', f'/games/{game_id}/clock', {'action': action})

    def command(self, game_id: str, envelope: Body) -> Body:
        return self._read('POST', f'/games/{game_id}/commands', envelope)

    def record(self, game_id: str) -> bytes:
        return self._ask('GET', f'/games/{game_id}/record').content

    def updates(self, game_id: str, after: int) -> Generator[Body]:
        """
        Every message of the stream until the game ends. An error of the stream is raised as it came.
        """
        url = f'{self._base.replace("http", "ws", 1)}/games/{game_id}/updates?after={after}'
        with connect(url) as socket:
            for text in socket:
                message: Body = json.loads(text)
                refused = _refusal(message)
                if refused is not None:
                    raise refused
                yield message

    def _ask(self, method: str, path: str, body: Body | None = None) -> httpx.Response:
        answer = self._http.request(method, path, json=body)
        if answer.is_error:
            try:
                refused = _refusal(answer.json())
            except ValueError:
                refused = None
            if refused is not None:
                raise refused
            answer.raise_for_status()
        return answer

    def _read(self, method: str, path: str, body: Body | None = None) -> Body:
        read: Body = self._ask(method, path, body).json()
        return read
