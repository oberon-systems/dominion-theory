"""
The client the store talks through: fakeredis in the process, or a Valkey server by its URL.
"""

from collections.abc import Iterable
from datetime import timedelta
from functools import lru_cache
from typing import Any, Protocol, cast

import fakeredis
import valkey


class Pipeline(Protocol):
    def set(self, name: str, value: bytes, ex: timedelta) -> object: ...

    def get(self, name: str) -> object: ...

    def delete(self, *names: str) -> object: ...

    def exists(self, *names: str) -> object: ...

    def expire(self, name: str, time: timedelta) -> object: ...

    def hset(self, name: str, *, mapping: dict[str, str]) -> object: ...

    def hgetall(self, name: str) -> object: ...

    def rpush(self, name: str, *values: bytes) -> object: ...

    def lrange(self, name: str, start: int, end: int) -> object: ...

    def sadd(self, name: str, *values: str) -> object: ...

    def srem(self, name: str, *values: str) -> object: ...

    def execute(self) -> list[Any]: ...


class Client(Protocol):
    def pipeline(self) -> Pipeline: ...

    def smembers(self, name: str) -> Iterable[bytes]: ...

    def srem(self, name: str, *values: str) -> int: ...


@lru_cache
def _server() -> fakeredis.FakeServer:
    return fakeredis.FakeServer(server_type='valkey')


def connect(url: str) -> Client:
    if url:
        return cast(Client, valkey.Valkey.from_url(url))
    return cast(Client, fakeredis.FakeValkey(server=_server()))
