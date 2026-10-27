"""
One seat of a game in step mode as a client keeps it: the band, the council, the standing and the cells seen.
"""

from collections.abc import Generator, Mapping
from contextlib import closing
from functools import cached_property
from typing import Any

from .api import Api, Body
from .drawing import Watched
from .lines import Unit, follow

PASS = 'pass'  # noqa: S105
VOTE = 'vote'
VIEW = (33, 17)


class Session:
    def __init__(self, api: Api, game_id: str) -> None:
        self.api = api
        self.game = game_id
        self.biomes = {biome['id']: biome for biome in api.biomes(game_id)['biomes']}
        self.colours = {name: biome['colour'] for name, biome in self.biomes.items()}
        self.watched = Watched()
        self.read(api.snapshot(game_id))

    def read(self, snapshot: Mapping[str, Any]) -> None:
        seat = snapshot['seat']
        self.seq: int = snapshot['seq']
        self.date: Body | None = snapshot.get('date')
        self.seat: str = seat['name']
        self.status: float = seat['status']
        self.council: Body | None = seat['council']
        self.band: Unit | None = next(iter(snapshot.get('units', [])), None)
        self.waiting: list[str] = snapshot['waiting']

    def apply(self, message: Mapping[str, Any]) -> None:
        changes = message.get('changes', {})
        seat = changes.get('seat', {})
        self.seq = message['seq']
        self.date = message['date']
        self.band = follow(self.band, message)
        self.council = seat.get('council', self.council)
        if seat.get('status') is not None:
            self.status = seat['status']
        self.waiting = message['waiting']
        self.watched.take(changes)

    def stream(self) -> Generator[Body]:
        """
        Every message after the snapshot, applied before it is given out; a resync re-reads the snapshot.
        """
        with closing(self.api.updates(self.game, self.seq)) as messages:
            for message in messages:
                if message.get('resync'):
                    self.read(self.api.snapshot(self.game))
                else:
                    self.apply(message)
                yield message

    @cached_property
    def skills(self) -> list[str]:
        """
        Every skill of the game in the order of its tree, asked of the server the first time it is wanted.
        """
        return list(self.api.params(self.game).get('skills', {}))

    @property
    def asked(self) -> bool:
        return self.seat in self.waiting

    @property
    def place(self) -> tuple[int, int] | None:
        return None if self.band is None else (self.band['place']['x'], self.band['place']['y'])

    @property
    def camps(self) -> list[tuple[int, int]]:
        return [] if self.band is None else [(held['x'], held['y']) for held in self.band.get('camps', [])]

    def answer(self, seq: int, proposal: Mapping[str, Any] | None = None) -> None:
        """
        Pass, or vote for the proposal while the council sits.
        """
        if proposal is None:
            self.api.command(self.game, {'id': f'{PASS}-{seq}', 'kind': PASS})
        else:
            self.api.command(self.game, {'id': f'{VOTE}-{seq}', 'kind': VOTE, 'proposal': dict(proposal)})

    def known(self) -> Body | None:
        """
        The rectangle of the view around the band as it knows it, or None with no band.
        """
        if self.band is None:
            return None
        (x, y), (width, height) = (self.band['place']['x'], self.band['place']['y']), VIEW
        known = self.api.map(self.game, x - width // 2, y - height // 2, width, height, known=self.band['id'])
        self.watched.learn(known)
        return known

    def stocked(self) -> None:
        if self.place is not None:
            self.watched.stocked(self.api.map(self.game, *self.place, 1, 1))
