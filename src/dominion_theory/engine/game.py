"""
The game: state and rules, advanced one tick at a time and by nothing else.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray

from ..content import Params, Property
from ..planet import Planet, biome_names, place
from . import band as bands
from . import council, decisions, encounters
from .band import Action, Band
from .cells import Cells, Place
from .clock import DAY_STARTED, SEASON_STARTED, Clock, Date
from .commands import ABSTAIN, BUILT, MOVE, VOTE, Command
from .counters import Counters
from .events import (
    BAND_DIED,
    BAND_STATE_BEGAN,
    BAND_STATE_ENDED,
    COMMAND_ACCEPTED,
    COMMAND_REFUSED,
    COUNCIL_ABSTAINED,
    COUNCIL_AGREED,
    COUNCIL_FOLLOWED,
    COUNCIL_OPENED,
    COUNCIL_OUTVOTED,
    COUNCIL_TURNED,
    ENCOUNTER,
    INTENT_ENDED,
    KIND,
    PEOPLE_BORN,
    PEOPLE_INJURED,
    PEOPLE_LOST,
    PROPOSAL_DISASTER,
    PROPOSAL_EVEN,
    PROPOSAL_FAILED,
    PROPOSAL_WORKED,
    REFUSED_ALREADY_VOTED,
    REFUSED_NO_COUNCIL,
    REFUSED_NO_SUCH_DIRECTION,
    REFUSED_SEAT_BANISHED,
    REFUSED_UNKNOWN_COMMAND,
    REFUSED_UNKNOWN_SEAT,
    SEAT_BANISHED,
    SEAT_BLAMED,
    SEAT_PRAISED,
    STATE,
    Event,
)
from .hashing import digest
from .streams import Streams

SNAPSHOT_FORMAT = 10
DIED = 'died'
BANISHED = 'banished'
VOTED = 'voted'
SILENT = 'silent'
ERA = 'band'
SEATS: tuple[str, ...] = ('player',)
UNIT_COLUMNS: tuple[str, ...] = bands.COLUMNS
TOTALS = ('moves', 'roams', 'gathers', 'camps', 'deaths', 'encounters')
VERDICTS = {
    council.WORKED: PROPOSAL_WORKED,
    council.EVEN: PROPOSAL_EVEN,
    council.FAILED: PROPOSAL_FAILED,
    council.DISASTER: PROPOSAL_DISASTER,
}

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
    known: list[dict[str, Any]] = field(default_factory=list)
    gone: list[int] = field(default_factory=list)
    shown: dict[str, Any] | None = None
    action: Action | None = None
    answers: dict[str, council.Proposal] = field(default_factory=dict)
    sat: bool = False
    seat: dict[str, Any] = field(default_factory=dict)


def _decides(game: Game, band: Band) -> Action:
    def pick(count: int) -> int:
        return int(game.streams['decisions'].integers(count))

    return decisions.decide(game.params, band, game.day, game.era, pick)


def _nothing_since(first: bool) -> dict[str, Any]:
    return {council.FIRST: first, council.DEATH: 0, council.CLOSED: False, council.SEASON: False, council.RIVER: False}


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
        band: Band | None = None,
        seated: bool = False,
    ) -> None:
        self.seed = seed
        self.params = params
        self.streams = streams
        self.window = window
        self.biomes = biomes
        self.rivers = rivers
        self.cells = Cells() if cells is None else cells
        self.band = band
        self.over = False
        self.outcome: str | None = None
        self.choose: Callable[[Game, Band], Action] = _decides
        self.era = ERA
        self.seats = SEATS
        self.tick = 0
        self.clock = Clock(params.time)
        self.unit_columns = UNIT_COLUMNS
        self._pending: list[tuple[int, Command]] = []
        self._sequence: dict[str, int] = {}
        self._seen: set[str] = set()
        self.status = params.council.status.start
        # An empty seat, as in a headless run, has no council: the band lives as if there were none.
        self.seated = seated
        self.council: dict[str, Any] | None = None
        self.judgement: dict[str, Any] | None = None
        # How the player answered the council of the day the band lives today, and of tomorrow: voted, silent or None.
        self.answered: dict[str, str | None] = {'today': None, 'tomorrow': None}
        # What happened since the last council, the occasions that may call the next one.
        self.since = _nothing_since(first=True)
        self._totals = {'commands_accepted': 0, 'commands_refused': 0, **dict.fromkeys(TOTALS, 0), 'councils': 0}
        self.counters = Counters()
        for name in ('commands_accepted', 'commands_refused'):
            self.counters.declare(name, partial(self._totals.__getitem__, name))
        self.counters.declare('cells_depleted', partial(len, self.cells))
        self.counters.declare('population', lambda: 0 if self.band is None else self.band.population)
        for name in bands.SHORTAGES:
            self.counters.declare(name, partial(self._held, name))
        for name in TOTALS:
            self.counters.declare(name, partial(self._totals.__getitem__, name))
        self.counters.declare('status', lambda: self.status)
        self.counters.declare('councils', partial(self._totals.__getitem__, 'councils'))
        for name in params.units.band.people.stages:
            self.counters.declare(name, partial(self._counted, name))
        for name in (bands.PREGNANT, bands.INJURED):
            self.counters.declare(name, partial(self._counted, name))

    @classmethod
    def create(cls, seed: int, params: Params, seated: bool = False) -> Self:
        streams = Streams(seed)
        size = params.planet.window
        x, y = place(seed, params)
        region = Planet(seed, params).read(x, y, size.width, size.height, params.eras[ERA].cell_km)
        window = Window(0, x, y, size.width, size.height)
        game = cls(seed, params, streams, window, region.biomes, region.rivers, seated=seated)
        found = game._start()
        if found is not None:
            game.band = bands.start(game, *found, game.day, streams['people'])
        if game.date.part == params.council.part:
            game._open(_Tick())
        return game

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
            next((Band.read(unit) for unit in snapshot['units']), None),
        )
        game.over, game.outcome = snapshot['over'], snapshot['outcome']
        seat = snapshot['seat']
        game.status, game.seated, game.council = seat['status'], seat['seated'], seat['council']
        game.judgement = snapshot['judgement']
        game.answered = dict(snapshot['answered'])
        game.since = dict(snapshot['since'])
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
    def seat(self) -> dict[str, Any]:
        """
        The seat as a client sees it: docs/game/01_bands.md, What the API shows.
        """
        unit = None if self.band is None else self.band.id
        return {
            'name': self.seats[0],
            'unit': unit,
            'status': self.status,
            'seated': self.seated,
            'council': self.council,
        }

    @property
    def asking(self) -> list[str]:
        """
        The seats the council of the day sits for.
        """
        return list(self.seats) if self.council is not None and not self.banished else []

    @property
    def banished(self) -> bool:
        return self.status <= 0

    @property
    def stocked(self) -> tuple[str, ...]:
        """
        The properties of the era that some biome lets recover, and so the stocks a cell is reported with.
        """
        biomes = self.params.biomes.values()
        names = self.params.eras[self.era].properties
        return tuple(name for name in names if any(biome.eras[self.era].properties[name].recovery for biome in biomes))

    @property
    def day(self) -> int:
        """
        The days gone since the start of the game.
        """
        return self.clock.parts // self.params.time.parts_per_day

    def inside(self, x: int, y: int) -> bool:
        window = self.window
        return window.x <= x < window.x + window.width and window.y <= y < window.y + window.height

    def biome(self, x: int, y: int) -> str:
        row, column = self._at(x, y)
        return biome_names(self.params)[int(self.biomes[row, column])]

    def river(self, x: int, y: int) -> bool:
        row, column = self._at(x, y)
        return bool(self.rivers[row, column])

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
            'units': [] if self.band is None else [self.band.plain()],
            'over': self.over,
            'outcome': self.outcome,
            'seat': self.seat,
            'judgement': self.judgement,
            'answered': dict(self.answered),
            'since': dict(self.since),
        }

    def _counted(self, name: str) -> float:
        if self.band is None:
            return 0
        counted = bands.census(self.params, self.band)
        return float(counted.counts[name] if name in counted.counts else getattr(counted, name))

    def _held(self, prop: str) -> float:
        if self.band is None:
            return 0.0
        resources = self.params.resources
        return sum(self.band.held(name) for name in self.band.stores if resources[name].property == prop)

    def _start(self) -> Place | None:
        """
        Where the band starts: the cell nearest the centre of the window among the start biomes,
        among all that can be entered when there is none; the smaller y, then x, of two equally near.
        """
        window, names = self.window, biome_names(self.params)
        eras = [self.params.biomes[name].eras[self.era] for name in names]
        walked = np.array([not era.shore and era.properties[bands.PASSABILITY].base > 0 for era in eras])
        wanted = walked & np.array([name in self.params.units.band.start.biomes for name in names])
        centre = (window.width - 1) / 2, (window.height - 1) / 2
        for fits in (wanted, walked):
            rows, columns = np.nonzero(fits[self.biomes])
            if rows.size:
                far = (columns - centre[0]) ** 2 + (rows - centre[1]) ** 2
                first = np.lexsort((columns, rows, far))[0]
                return window.x + int(columns[first]), window.y + int(rows[first])
        return None

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
        era = self.params.eras[self.era]
        shares = {}
        for name in self.stocked:
            recovery = self._property(name, row, column).recovery
            if recovery is not None:
                pace = era.recovery.get(name, {}).get(self.date.season, 1.0)
                shares[name] = pace * era.parts_per_tick / self.clock.to_parts(recovery)
        return shares

    def _judge(self, command: Command, answered: dict[str, council.Proposal]) -> str | None:
        if command.seat not in self.seats:
            return REFUSED_UNKNOWN_SEAT
        if self.banished:
            return REFUSED_SEAT_BANISHED
        if command.kind not in BUILT:
            return REFUSED_UNKNOWN_COMMAND
        if command.kind == VOTE:
            return self._refusal(council.answer(command.fields), command.seat in answered)
        return None

    def _refusal(self, answer: council.Proposal | None, voted: bool) -> str | None:
        """
        Why a vote is not taken now, in the order of docs/game/indirect_control.md.
        """
        if answer is None or self.band is None:
            return REFUSED_UNKNOWN_COMMAND
        if self.council is None:
            return REFUSED_NO_COUNCIL
        if voted:
            return REFUSED_ALREADY_VOTED
        if answer['kind'] == MOVE and decisions.way(self.params, self.band, answer['towards'], self.era) is None:
            return REFUSED_NO_SUCH_DIRECTION
        return None

    def _commands(self, tick: _Tick) -> None:
        for _, command in sorted(self._pending, key=lambda held: (held[1].seat, held[0])):
            reason = self._judge(command, tick.answers)
            if reason is None:
                self._totals['commands_accepted'] += 1
                tick.events.append(Event(COMMAND_ACCEPTED, {'id': command.id}))
                answer = council.answer(command.fields) if command.kind == VOTE else None
                if answer is not None:
                    tick.answers[command.seat] = answer
            else:
                self._totals['commands_refused'] += 1
                tick.events.append(Event(COMMAND_REFUSED, {'id': command.id, 'reason': reason}))
        self._pending.clear()

    def _open(self, tick: _Tick) -> None:
        """
        The council of the evening, when an occasion calls it: the intent before ends and is judged, then the
        others' votes are laid out. Without an occasion the last decision stands.
        """
        band = self.band
        if band is None or self.over or not self.seated:
            return
        laid = council.table(self.params, band, self.era)
        occasion = self._occasion(band, laid)
        if occasion is None:
            return
        self.since = _nothing_since(first=False)
        band.intent = None
        if self.judgement is not None:
            self._verdict(tick, band, self.judgement)
            if self.over:
                return
        leader = council.leader(laid)
        values = {'leader': council.key(leader), 'occasion': f'{council.OCCASION}{occasion}'}
        if council.settled(laid, council.voice(self.params, bands.voters(self.params, band), self.status)):
            self.answered['tomorrow'] = VOTED
            self._bind(band, leader)
            tick.events.append(Event(COUNCIL_AGREED, values))
            return
        self.council = tick.seat['council'] = {'leader': leader, 'table': laid}
        self._totals['councils'] += 1
        tick.events.append(Event(COUNCIL_OPENED, values))

    def _occasion(self, band: Band, laid: council.Table) -> str | None:
        """
        The first of the occasions that holds this evening, None when nothing calls the council.
        """
        since = self.since
        hungry = max(decisions.needs(self.params, band).values()) >= self.params.units.band.roaming.hunger
        held = {
            council.FIRST: since[council.FIRST],
            council.DEATH: since[council.DEATH] > 0,
            council.HUNGER: hungry,
            council.CLOSED: since[council.CLOSED],
            council.RESTLESS: council.restless(laid, None if band.intent is None else band.intent['proposal']),
            council.SEASON: since[council.SEASON],
            council.RIVER: since[council.RIVER],
        }
        return next((name for name in council.OCCASIONS if held[name]), None)

    def _councils(self, tick: _Tick) -> None:
        band = self.band
        if band is None:
            return
        tick.shown = band.shown(self.params, self.window.scale)
        sitting = self.council
        if sitting is None:
            return
        self.council = tick.seat['council'] = None
        tick.sat = True
        answer = tick.answers.get(self.seats[0])
        self.answered['tomorrow'] = SILENT
        if answer is None or answer['kind'] == ABSTAIN:
            self._bind(band, sitting['leader'])
            self._status(tick, self.params.council.status.abstained)
            tick.events.append(Event(COUNCIL_ABSTAINED, {'status': self.status}))
            self._banish(tick)
            return
        spoken = council.voice(self.params, bands.voters(self.params, band), self.status)
        winner, yes = council.decide(sitting['table'], answer, spoken)
        self.answered['tomorrow'] = VOTED if winner == answer else None
        self._bind(band, winner)
        if winner != answer:
            self._status(tick, self.params.council.status.outvoted)
            values = {'proposal': council.key(answer), 'winner': council.key(winner), 'status': self.status}
            tick.events.append(Event(COUNCIL_OUTVOTED, values))
            self._banish(tick)
        elif answer == sitting['leader']:
            tick.events.append(Event(COUNCIL_FOLLOWED, {'proposal': council.key(answer)}))
        else:
            every = bands.voters(self.params, band) - 1 + spoken
            tick.events.append(Event(COUNCIL_TURNED, {'proposal': council.key(answer), 'yes': yes, 'all': every}))
            self.judgement = {
                'proposal': answer,
                'population': band.population,
                'needs': decisions.needs(self.params, band),
                'expected': council.expected(self.params, band, self.era, sitting['leader']),
                'before': council.reached(self.params, band, decisions.needs(self.params, band), band.unease),
                'unease': band.unease,
                'lost': {},
            }

    @staticmethod
    def _bind(band: Band, decided: council.Proposal | None) -> None:
        band.intent = None if decided is None else {'proposal': dict(decided)}

    def _decisions(self, tick: _Tick) -> None:
        band = self.band
        if band is None:
            return
        if tick.sat or self.date.part in self.params.units.band.camp_parts:
            camped = decisions.Scored(bands.camp(), 0.0, decisions.REST)
            band.wander, band.reason = None, decisions.reason(camped)
            tick.action = camped.action
            return
        if band.intent is not None:
            proposal = band.intent['proposal']
            held = decisions.intended(self.params, band, proposal, self.era)
            if held is not None:
                band.wander, band.reason = None, decisions.reason(held)
                tick.action = held.action
                return
            band.intent = None
            self.since[council.CLOSED] = True
            tick.events.append(Event(INTENT_ENDED, {'proposal': council.key(proposal)}))
        tick.action = self.choose(self, band)

    def _actions(self, tick: _Tick) -> None:
        band = self.band
        if band is None or tick.action is None:
            return
        done = bands.act(self, band, tick.action, self.day)
        self._totals[f'{done["kind"]}s'] += 1
        self._states(tick, *bands.tire(self.params.units.band, band))
        before = set(band.known)
        tick.known = [{'x': x, 'y': y, **band.known[x, y]} for x, y in bands.look(self, band, self.day)]
        if any(cell['river'] and (cell['x'], cell['y']) not in before for cell in tick.known):
            self.since[council.RIVER] = True

    def _world(self, tick: _Tick) -> None:
        tick.cells = self.cells.regain(self._regained)
        band = self.band
        if band is None:
            return
        per_day, span = self.params.time.parts_per_day, self.params.eras[self.era].parts_per_tick
        parts = self.clock.parts
        if parts % per_day < span:
            bands.spoil(self.params, band, self.day)
        self._encounter(tick, band)
        if (parts + span) // per_day > parts // per_day:
            self._day_ends(tick, band)
        if band.population < self.params.units.band.population.least:
            tick.events.append(Event(BAND_DIED, {}))
            tick.gone.append(band.id)
            self.band, self.over, self.outcome = None, True, DIED

    def _lost(self, tick: _Tick, cause: str, count: int) -> None:
        """
        People who died: of a cause the council is blamed for, counted against a judgement, and against the
        player who voted or kept silent on the day.
        """
        self._totals['deaths'] += count
        tick.events.append(Event(PEOPLE_LOST, {'count': count, 'cause': cause}))
        if cause not in self.params.council.blamed:
            return
        self.since[council.DEATH] += count
        if self.judgement is not None:
            lost = self.judgement['lost']
            lost[cause] = lost.get(cause, 0) + count
        if self.answered['today'] is not None and not self.banished:
            self._status(tick, self.params.council.status.death * count)
            tick.events.append(Event(SEAT_BLAMED, {'lost': count, 'status': self.status}))
            self._banish(tick)

    def _verdict(self, tick: _Tick, band: Band, judgement: dict[str, Any]) -> None:
        self.judgement = None
        proposal = judgement['proposal']
        # The land reached is weighed with the unease of the day it was promised, as the promise was.
        now = council.reached(self.params, band, judgement['needs'], judgement['unease'])
        found = council.verdict(self.params, judgement, now)
        self._status(tick, council.amount(self.params, proposal, found))
        values: dict[str, Any] = {'proposal': council.key(proposal), 'status': self.status}
        if found in (council.FAILED, council.DISASTER):
            values['lost'] = sum(judgement['lost'].values())
        tick.events.append(Event(VERDICTS[found], values))
        self._banish(tick)

    def _status(self, tick: _Tick, amount: float) -> None:
        status = council.held(self.status + council.scaled(amount, self.status))
        if status != self.status:
            self.status = tick.seat['status'] = status

    def _banish(self, tick: _Tick) -> None:
        if self.banished and self.outcome != BANISHED:
            tick.events.append(Event(SEAT_BANISHED, {}))
            self.over, self.outcome = True, BANISHED

    def _encounter(self, tick: _Tick, band: Band) -> None:
        threat = self.value('threat', band.x, band.y)
        biome, river = self.biome(band.x, band.y), self.river(band.x, band.y)
        rng = self.streams['encounters']
        met = encounters.strike(self.params, biome, river, threat, band.action, rng)
        if met is None:
            return
        kind, taken, hurt = met
        lost, injured = bands.struck(self.params, band, taken, hurt, self.day, self.streams['people'])
        if lost or injured:
            bands.frighten(self.params, band)
        self._totals['encounters'] += 1
        tick.events.append(Event(ENCOUNTER, {'kind': f'{KIND}{kind}', 'lost': lost}))
        if lost:
            self._lost(tick, bands.ENCOUNTER, lost)
        if injured:
            tick.events.append(Event(PEOPLE_INJURED, {'count': injured}))

    def _day_ends(self, tick: _Tick, band: Band) -> None:
        people = self.streams['people']
        feeds = bands.fed(self.params, band)
        began, ended, lost = bands.suffer(self.params, band, bands.eat(self.params, band), people)
        self._states(tick, began, ended)
        for cause, count in lost:
            self._lost(tick, cause, count)
        threat = self.value(decisions.THREAT, band.x, band.y)
        lived = bands.live(self.params, band, self.day, decisions.wellbeing(self.params, band, threat), feeds, people)
        bands.unsettle(self.params, band, threat)
        for cause, count in lived.lost:
            self._lost(tick, cause, count)
        if lived.injured:
            tick.events.append(Event(PEOPLE_INJURED, {'count': lived.injured}))
        born = lived.born
        if born:
            tick.events.append(Event(PEOPLE_BORN, {'count': born}))
            if self.answered['today'] == VOTED and not self.banished:
                self._status(tick, self.params.council.status.birth * born)
                tick.events.append(Event(SEAT_PRAISED, {'born': born, 'status': self.status}))

    def _states(self, tick: _Tick, began: list[str], ended: list[str]) -> None:
        tick.events.extend(Event(BAND_STATE_ENDED, {'state': f'{STATE}{state}'}) for state in ended)
        tick.events.extend(Event(BAND_STATE_BEGAN, {'state': f'{STATE}{state}'}) for state in began)

    def _calendar(self, tick: _Tick) -> None:
        self.tick += 1
        for boundary in self.clock.advance(self.params.eras[self.era].parts_per_tick):
            tick.events.append(Event(boundary.key, boundary.values))
            if boundary.key == DAY_STARTED:
                self.answered['today'] = self.answered['tomorrow']
            if boundary.key == SEASON_STARTED:
                self.since[council.SEASON] = True
        if self.date.part == self.params.council.part:
            self._open(tick)

    def _report(self, tick: _Tick) -> None:
        stocked = self.stocked
        cells = [{'x': x, 'y': y, **{name: self.cells.stock((x, y), name) for name in stocked}} for x, y in tick.cells]
        units = []
        if self.band is not None:
            shown = self.band.shown(self.params, self.window.scale)
            units = [shown] if shown != tick.shown else []
            tick.units.append(self.band.row(self.params))
        tick.changes.update({'units': units, 'gone': tick.gone, 'cells': cells, 'known': tick.known, 'seat': tick.seat})
        tick.counters.extend(self.counters.row())
