"""
The game: state and rules, advanced one tick at a time and by nothing else.
"""

from dataclasses import asdict, dataclass, field
from functools import partial
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray

from ..content import Params
from ..planet import BIOMES, generate
from .clock import Clock, Date
from .commands import BUILT, Command
from .counters import Counters
from .events import COMMAND_ACCEPTED, COMMAND_REFUSED, REFUSED_UNKNOWN_COMMAND, REFUSED_UNKNOWN_SEAT, Event
from .hashing import digest
from .streams import Streams

SNAPSHOT_FORMAT = 1
ERA = 'band'
SEATS: tuple[str, ...] = ('player',)
RIVERS = 'rivers'
UNIT_COLUMNS: tuple[str, ...] = ()

# The order is part of the rules: docs/architecture/overview.md, One tick.
PHASES = ('commands', 'councils', 'decisions', 'actions', 'world', 'calendar', 'report')


@dataclass(frozen=True)
class Window:
    """
    The rectangle of the planet the game is played on, in cells of its scale.
    """

    scale: int
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class StepResult:
    tick: int
    parts: int
    date: Date
    events: list[Event]
    changes: dict[str, Any]
    counters: list[float]
    units: list[list[Any]]
    hash: str


@dataclass
class _Tick:
    events: list[Event] = field(default_factory=list)
    changes: dict[str, Any] = field(default_factory=dict)
    counters: list[float] = field(default_factory=list)
    units: list[list[Any]] = field(default_factory=list)


class Game:
    def __init__(
        self,
        seed: int,
        params: Params,
        streams: Streams,
        window: Window,
        biomes: NDArray[np.uint8],
    ) -> None:
        self.seed = seed
        self.params = params
        self.streams = streams
        self.window = window
        self.biomes = biomes
        self.era = ERA
        self.seats = SEATS
        self.tick = 0
        self.clock = Clock(params.time)
        self.unit_columns = UNIT_COLUMNS
        self._pending: list[tuple[int, Command]] = []
        self._sequence: dict[str, int] = {}
        self._seen: set[str] = set()
        self._totals = {'commands_accepted': 0, 'commands_refused': 0}
        self.counters = Counters()
        for name in self._totals:
            self.counters.declare(name, partial(self._totals.__getitem__, name))

    @classmethod
    def create(cls, seed: int, params: Params) -> Self:
        streams = Streams(seed)
        size = params.planet.window
        biomes = generate(seed=seed, width=size.width, height=size.height, rivers=streams[RIVERS])
        return cls(seed, params, streams, Window(0, 0, 0, size.width, size.height), biomes)

    @classmethod
    def restore(cls, snapshot: dict[str, Any]) -> Self:
        if snapshot['format'] != SNAPSHOT_FORMAT:
            raise ValueError(f'a snapshot of format {snapshot["format"]} cannot be read')
        game = cls(
            snapshot['seed'],
            Params.model_validate(snapshot['params']),
            Streams(snapshot['seed'], snapshot['streams']),
            Window(**snapshot['window']),
            np.array(snapshot['grids']['biomes'], dtype=np.uint8),
        )
        commands = snapshot['commands']
        game.era = snapshot['era']
        game.tick = snapshot['tick']
        game.clock.parts = snapshot['parts']
        game._pending = [(held['seq'], Command.read(held['seat'], held['command'])) for held in commands['pending']]
        game._sequence = dict(commands['sequence'])
        game._seen = set(commands['seen'])
        game._totals.update(snapshot['counters'])
        return game

    @property
    def date(self) -> Date:
        return self.clock.date

    def submit(self, command: Command) -> None:
        seq = self._sequence.get(command.seat, 0) + 1
        if command.id is None:
            command = command.named(f'{command.seat}-{seq}')
        if command.id in self._seen:
            return
        self._seen.add(str(command.id))
        self._sequence[command.seat] = seq
        self._pending.append((seq, command))

    def step(self) -> StepResult:
        tick = _Tick()
        for phase in PHASES:
            getattr(self, f'_{phase}')(tick)
        return StepResult(
            tick=self.tick,
            parts=self.clock.parts,
            date=self.date,
            events=tick.events,
            changes=tick.changes,
            counters=tick.counters,
            units=tick.units,
            hash=self.state_hash(),
        )

    def snapshot(self) -> dict[str, Any]:
        return {**self._plain(), 'params': self.params.tree(), 'grids': {'biomes': self.biomes.copy()}}

    def state_hash(self) -> str:
        return digest({**self._plain(), 'params': self.params.hash}, {'biomes': self.biomes})

    def _plain(self) -> dict[str, Any]:
        pending = [{'seat': command.seat, 'seq': seq, 'command': command.envelope()} for seq, command in self._pending]
        return {
            'format': SNAPSHOT_FORMAT,
            'seed': self.seed,
            'era': self.era,
            'tick': self.tick,
            'parts': self.clock.parts,
            'window': asdict(self.window),
            'streams': self.streams.states(),
            'commands': {
                'pending': pending,
                'sequence': dict(sorted(self._sequence.items())),
                'seen': sorted(self._seen),
            },
            'counters': dict(self._totals),
            'biomes': list(BIOMES),
        }

    def _judge(self, command: Command) -> str | None:
        if command.seat not in self.seats:
            return REFUSED_UNKNOWN_SEAT
        if command.kind not in BUILT:
            return REFUSED_UNKNOWN_COMMAND
        return None

    def _commands(self, tick: _Tick) -> None:
        for _, command in sorted(self._pending, key=lambda held: (held[1].seat, held[0])):
            reason = self._judge(command)
            if reason is None:
                self._totals['commands_accepted'] += 1
                tick.events.append(Event(COMMAND_ACCEPTED, {'id': command.id}))
            else:
                self._totals['commands_refused'] += 1
                tick.events.append(Event(COMMAND_REFUSED, {'id': command.id, 'reason': reason}))
        self._pending.clear()

    def _councils(self, tick: _Tick) -> None:
        pass

    def _decisions(self, tick: _Tick) -> None:
        pass

    def _actions(self, tick: _Tick) -> None:
        pass

    def _world(self, tick: _Tick) -> None:
        pass

    def _calendar(self, tick: _Tick) -> None:
        self.tick += 1
        for boundary in self.clock.advance(self.params.eras[self.era].parts_per_tick):
            tick.events.append(Event(boundary.key, boundary.values))

    def _report(self, tick: _Tick) -> None:
        tick.changes.update({'units': [], 'gone': [], 'cells': [], 'seat': {}})
        tick.counters.extend(self.counters.row())
