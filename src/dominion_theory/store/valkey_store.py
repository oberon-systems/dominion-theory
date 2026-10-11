"""
The one implementation of the game store, over the Valkey client interface.
"""

import json
from datetime import timedelta
from typing import Any

from .base import Meta, Stored
from .client import Client, Pipeline
from .codec import dumps, pack, unpack

PREFIX = 'dt:'
GAMES = f'{PREFIX}games'
META = 'meta'
SNAPSHOT = 'snapshot'
CHANGES = 'changes'
PARTS = (META, SNAPSHOT, CHANGES)


def key(game_id: str, part: str) -> str:
    return f'{PREFIX}game:{game_id}:{part}'


class ValkeyStore:
    def __init__(self, client: Client, ttl: timedelta) -> None:
        self.client = client
        self.ttl = ttl

    def save_snapshot(self, game_id: str, snapshot: dict[str, Any], meta: Meta) -> None:
        pipe = self.client.pipeline()
        pipe.set(key(game_id, SNAPSHOT), pack(snapshot), ex=self.ttl)
        pipe.delete(key(game_id, CHANGES))
        pipe.hset(
            key(game_id, META),
            mapping={'seed': str(meta.seed), 'params': meta.params, 'tick': str(meta.tick), 'mode': meta.mode},
        )
        pipe.sadd(GAMES, game_id)
        self._renew(pipe, game_id)
        pipe.execute()

    def append_changes(self, game_id: str, tick: int, changes: dict[str, Any]) -> None:
        pipe = self.client.pipeline()
        pipe.rpush(key(game_id, CHANGES), dumps(changes))
        pipe.hset(key(game_id, META), mapping={'tick': str(tick)})
        self._renew(pipe, game_id)
        pipe.execute()

    def load(self, game_id: str) -> Stored | None:
        pipe = self.client.pipeline()
        pipe.get(key(game_id, SNAPSHOT))
        pipe.lrange(key(game_id, CHANGES), 0, -1)
        pipe.hgetall(key(game_id, META))
        snapshot, changes, meta = pipe.execute()
        if snapshot is None or not meta:
            return None
        held = {name.decode(): value.decode() for name, value in meta.items()}
        return Stored(
            meta=Meta(seed=int(held['seed']), params=held['params'], tick=int(held['tick']), mode=held['mode']),
            snapshot=unpack(snapshot),
            changes=[json.loads(entry) for entry in changes],
        )

    def live_games(self) -> list[str]:
        listed = sorted(member.decode() for member in self.client.smembers(GAMES))
        pipe = self.client.pipeline()
        for game_id in listed:
            pipe.exists(key(game_id, SNAPSHOT))
        # A game whose keys expired is still in the set, which never expires.
        gone = [game_id for game_id, there in zip(listed, pipe.execute(), strict=True) if not there]
        if gone:
            self.client.srem(GAMES, *gone)
        return [game_id for game_id in listed if game_id not in gone]

    def drop(self, game_id: str) -> None:
        pipe = self.client.pipeline()
        pipe.delete(*(key(game_id, part) for part in PARTS))
        pipe.srem(GAMES, game_id)
        pipe.execute()

    def _renew(self, pipe: Pipeline, game_id: str) -> None:
        for part in PARTS:
            pipe.expire(key(game_id, part), self.ttl)
