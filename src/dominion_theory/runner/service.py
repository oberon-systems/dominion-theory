"""
The live games of a server: created, found, ended, and picked up again after a restart.
"""

import secrets
from functools import partial
from typing import Any

from ..content import load_params, presets
from ..core.errors import DominionError
from ..core.settings import Settings, get_settings
from ..engine import Game
from ..store import GameStore, open_store
from .record import RecordWriter, header_line, record_path
from .runner import REAL_TIME, RUNNERS, STOPPED, Runner
from .updates import Ended, Update

GAME_NOT_FOUND = 'error-game-not-found'
SEED_BITS = 32


class Service:
    def __init__(self, store: GameStore | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.store = store or open_store(self.settings)
        self._runners: dict[str, Runner] = {}

    def create(
        self,
        seed: int | None = None,
        preset: str | None = None,
        overrides: dict[str, Any] | None = None,
        mode: str = REAL_TIME,
        seats: dict[str, str] | None = None,
        seated: bool = False,
        draw: int = 0,
    ) -> Runner:
        params = load_params(preset, overrides)
        seed = secrets.randbits(SEED_BITS) if seed is None else seed
        game = Game.create(seed=seed, params=params, seated=seated, draw=draw)
        runner = self._runner(self._new_id(), game, mode, seats=seats)
        runner.save()
        return runner

    def presets(self) -> list[str]:
        return presets()

    def find(self, game_id: str) -> Runner:
        if game_id not in self._runners:
            raise DominionError(GAME_NOT_FOUND, id=game_id)
        return self._runners[game_id]

    def games(self) -> list[Runner]:
        return list(self._runners.values())

    def end(self, game_id: str, outcome: str = STOPPED) -> Ended:
        return self.find(game_id).end(outcome)

    def restore(self) -> list[Runner]:
        """
        Every game the store lists comes back paused, at the tick it stopped.
        """
        restored = []
        for game_id in self.store.live_games():
            stored = None if game_id in self._runners else self.store.load(game_id)
            if stored is None:
                continue
            game = Game.restore(stored.snapshot)
            runner = self._runner(game_id, game, stored.meta.mode, seq=stored.snapshot.get('seq', 0))
            runner.catch_up(stored.changes)
            restored.append(runner)
        return restored

    def _new_id(self) -> str:
        while True:
            game_id = secrets.token_hex(4)
            # A record is kept after its game, so its name is never given twice.
            if not record_path(self.settings.records_dir, game_id).exists():
                return game_id

    def _runner(
        self,
        game_id: str,
        game: Game,
        mode: str,
        seq: int = 0,
        seats: dict[str, str] | None = None,
    ) -> Runner:
        kind = RUNNERS[mode]
        path = record_path(self.settings.records_dir, game_id)
        record = RecordWriter(path, header_line(game_id, game, seats))
        runner = kind(game_id, game, self.store, record, self.settings, seq)
        self._runners[game_id] = runner
        runner.subscribe(partial(self._heard, game_id))
        return runner

    def _heard(self, game_id: str, message: Update | Ended) -> None:
        if isinstance(message, Ended):
            self._runners.pop(game_id, None)
