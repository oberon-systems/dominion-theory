"""
The index of games of docs/architecture/records.md, kept by listening to the runners.
"""

import time
from functools import partial

from sqlmodel import col, select

from ..core.errors import DominionError
from ..db import LOCAL_PROFILE, Database, add_game
from ..db import Game as Row
from ..runner import GAME_NOT_FOUND, Ended, Runner, Update


class Index:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, runner: Runner, preset: str | None = None) -> Row:
        row = Row(
            id=runner.id,
            profile_id=LOCAL_PROFILE,
            seed=runner.game.seed,
            params_hash=runner.game.params.hash,
            preset=preset,
            record_path=str(runner.record_path),
        )
        with self._database.session() as session:
            add_game(session, row)
        self.follow(runner)
        return row

    def follow(self, runner: Runner) -> None:
        runner.subscribe(partial(self._heard, runner.id))

    def find(self, game_id: str) -> Row:
        with self._database.session() as session:
            row = session.get(Row, game_id)
        if row is None:
            raise DominionError(GAME_NOT_FOUND, id=game_id)
        return row

    def rows(self) -> list[Row]:
        mine = select(Row).where(Row.profile_id == LOCAL_PROFILE).order_by(col(Row.started_at), col(Row.id))
        with self._database.session() as session:
            return list(session.exec(mine).all())

    def _heard(self, game_id: str, message: Update | Ended) -> None:
        if not isinstance(message, Ended):
            return
        with self._database.session() as session:
            row = session.get(Row, game_id)
            if row is None:
                return
            row.last_tick = message.tick
            row.outcome = message.outcome
            row.finished_at = int(time.time())
            session.add(row)
            session.commit()
