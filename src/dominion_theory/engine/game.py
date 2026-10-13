"""
The game: state and rules, advanced one tick at a time and by nothing else.
"""

from dataclasses import asdict, dataclass, field
from functools import partial
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray

from ..content import Params, Property
from ..planet import Planet, biome_names, place
from .cells import Cells, Place
from .clock import Clock, Date
from .commands import BUILT, Command
from .counters import Counters
from .events import COMMAND_ACCEPTED, COMMAND_REFUSED, REFUSED_UNKNOWN_COMMAND, REFUSED_UNKNOWN_SEAT, Event
from .hashing import digest
from .streams import Streams

SNAPSHOT_FORMAT = 2
ERA = 'band'
SEATS: tuple[str, ...] = ('player',)
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
    cells: list[Place] = field(default_factory=list)


class Game:
    def __init__(
        self,
        seed: int,
        params: Params,
        streams: Streams,
        window: Window,
        biomes: NDArray[np.uint8],
        rivers: NDArray[np.bool_],
        cells: Cells | None = None,
    ) -> None:
        self.seed = seed
        self.params = params
        self.streams = streams
        self.window = window
        self.biomes = biomes
        self.rivers = rivers
        self.cells = Cells() if cells is None else cells
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
        self.counters.declare('cells_depleted', partial(len, self.cells))

    @classmethod
    def create(cls, seed: int, params: Params) -> Self:
        streams = Streams(seed)
        size = params.planet.window
        x, y = place(seed, params)
        region = Planet(seed, params).read(x, y, size.width, size.height, params.eras[ERA].cell_km)
        return cls(seed, params, streams, Window(0, x, y, size.width, size.height), region.biomes, region.rivers)

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
            np.array(snapshot['grids']['rivers'], dtype=np.bool_),
            Cells(snapshot['cells']),
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

    @property
    def stocked(self) -> tuple[str, ...]:
        """
        The properties of the era that some biome lets recover, and so the stocks a cell is reported with.
        """
        biomes = self.params.biomes.values()
        names = self.params.eras[self.era].properties
        return tuple(name for name in names if any(biome.eras[self.era].properties[name].recovery for biome in biomes))

    def value(self, name: str, x: int, y: int) -> float:
        """
        A property of the era at a planet cell of the window: (base + every plus) * every times * stock.
        """
        row, column = self._at(x, y)
        held = self._property(name, row, column)
        modifiers = [held.seasons.get(self.date.season)]
        if self.rivers[row, column]:
            modifiers.append(self.params.planet.rivers.effects.get(self.era, {}).get(name))
        plus, times = held.base, self.cells.stock((x, y), name)
        for modifier in modifiers:
            if modifier is not None and modifier.kind == 'plus':
                plus += modifier.amount
            elif modifier is not None:
                times *= modifier.amount
        return min(max(plus * times, 0.0), 1.0)

    def deplete(self, x: int, y: int, name: str, amount: float) -> None:
        """
        Lowers a stock of a cell, not below 0. For the rules of the game; it is not a command.
        """
        row, column = self._at(x, y)
        if self._property(name, row, column).recovery is None:
            raise ValueError(f'the property {name} does not recover at {x}, {y} and has no stock')
        if amount < 0:
            raise ValueError(f'a stock is lowered by an amount that is not negative, not by {amount}')
        self.cells.lower((x, y), name, amount)

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
        grids = {'biomes': self.biomes.copy(), 'rivers': self.rivers.copy()}
        return {**self._plain(), 'params': self.params.tree(), 'grids': grids}

    def state_hash(self) -> str:
        return digest({**self._plain(), 'params': self.params.hash}, {'biomes': self.biomes, 'rivers': self.rivers})

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
            'biomes': list(biome_names(self.params)),
            'cells': self.cells.plain(),
        }

    def _at(self, x: int, y: int) -> tuple[int, int]:
        window = self.window
        row, column = y - window.y, x - window.x
        if not (0 <= row < window.height and 0 <= column < window.width):
            raise ValueError(f'the cell {x}, {y} lies outside the window')
        return row, column

    def _property(self, name: str, row: int, column: int) -> Property:
        if name not in self.params.eras[self.era].properties:
            raise ValueError(f'the era {self.era} has no property {name}')
        biome = biome_names(self.params)[int(self.biomes[row, column])]
        return self.params.biomes[biome].eras[self.era].properties[name]

    def _regained(self, at: Place) -> dict[str, float]:
        row, column = self._at(*at)
        span = self.params.eras[self.era].parts_per_tick
        shares = {}
        for name in self.stocked:
            recovery = self._property(name, row, column).recovery
            if recovery is not None:
                shares[name] = span / self.clock.to_parts(recovery)
        return shares

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
        tick.cells = self.cells.regain(self._regained)

    def _calendar(self, tick: _Tick) -> None:
        self.tick += 1
        for boundary in self.clock.advance(self.params.eras[self.era].parts_per_tick):
            tick.events.append(Event(boundary.key, boundary.values))

    def _report(self, tick: _Tick) -> None:
        stocked = self.stocked
        cells = [{'x': x, 'y': y, **{name: self.cells.stock((x, y), name) for name in stocked}} for x, y in tick.cells]
        tick.changes.update({'units': [], 'gone': [], 'cells': cells, 'seat': {}})
        tick.counters.extend(self.counters.row())
