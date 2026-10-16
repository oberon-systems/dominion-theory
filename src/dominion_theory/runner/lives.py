"""
A band lived headless, with no player and no server, as a row a year from its counters; and the lives
of a few seeds kept in a file, so that a change of how a band lives is seen.
"""

import json
import math
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import click

from ..content import CAUSES, Params, load_params
from ..engine import Game
from ..engine.events import PEOPLE_BORN, PEOPLE_LOST
from ..store.codec import pack
from .service import SEED_BITS

SEEDS = (1, 2, 3, 4, 5)
YEARS = 18
FIRST = tuple(range(1, 51))
KB = 1024
# The size at which a band becomes a tribe, from the notes of stage 5 in docs/roadmap.md; not a rule yet.
TRIBE = 150
ALIVE = 'alive'
PACKAGE = Path(__file__).parents[1]
SOURCES = (
    Path(__file__),
    PACKAGE / 'store' / 'codec.py',
    *(path for name in ('content', 'engine', 'planet') for path in sorted((PACKAGE / name).glob('*.py'))),
)
PEOPLE = ('child', 'adult', 'elder', 'pregnant', 'injured')
LEVELS = {
    'people': 'population',
    **{name: name for name in PEOPLE},
    'food': 'food',
    'water': 'water',
    'status': 'status',
}
TOTALS = ('deaths', 'moves', 'roams', 'gathers', 'camps', 'builds', 'encounters')
STATES = {'starvation': 'starving', 'thirst': 'thirsty', 'tiredness': 'tired'}
YEAR = (
    'year',
    'people',
    *PEOPLE,
    'growth',
    'rate',
    'least',
    'born',
    'grown',
    'child-deaths',
    'deaths',
    *(f'of-{cause}' for cause in CAUSES),
    'food',
    'water',
    'moves',
    'roams',
    'gathers',
    'camps',
    'builds',
    *STATES.values(),
    'encounters',
    'status',
    'known',
    'snapshot',
)


@dataclass(frozen=True)
class Lived:
    seed: int
    start: int
    years: list[dict[str, float]]
    outcome: str
    tick: int
    hashes: tuple[str, ...] = ()
    packing: float = 0.0

    @property
    def growth(self) -> float | None:
        """
        The share the band grew by in a year, compounded over the whole years it lived; None if it died.
        """
        if self.outcome != ALIVE or not self.years or min(self.start, self.years[-1]['people']) <= 0:
            return None
        return float((self.years[-1]['people'] / self.start) ** (1 / len(self.years)) - 1)

    @property
    def tribe(self) -> float | None:
        """
        In how many years from the start the band reaches TRIBE at that growth; None if never.
        """
        growth, people = self.growth, self.years[-1]['people'] if self.years else 0
        if growth is None or growth <= 0:
            return None
        return len(self.years) + max(math.log(TRIBE / people) / math.log(1 + growth), 0.0)

    def data(self) -> dict[str, Any]:
        growth, tribe = self.growth, self.tribe
        return {
            'outcome': self.outcome,
            'tick': self.tick,
            'growth': None if growth is None else round(growth, 4),
            'tribe': None if tribe is None else round(tribe, 1),
            'years': self.years,
            'hashes': list(self.hashes),
        }

    def lines(self) -> list[str]:
        growth, tribe = self.growth, self.tribe
        grew = 'no growth' if growth is None else f'grows {growth:.1%} a year'
        reached = f'{TRIBE} people never' if tribe is None else f'{TRIBE} people in year {math.ceil(tribe)}'
        grown = sum(row['grown'] for row in self.years)
        left = grown + sum(row['child-deaths'] for row in self.years)
        raised = f'{int(grown)} of {int(left)} children grew up'
        return [*table(self.years), f'{self.outcome} at tick {self.tick}: {grew}, {reached}, {raised}']


def live(seed: int | None, years: int, preset: str | None = None, overrides: dict[str, Any] | None = None) -> Lived:
    params = load_params(preset, overrides)
    game = Game.create(seed=secrets.randbits(SEED_BITS) if seed is None else seed, params=params)
    start = 0 if game.band is None else game.band.population
    rows, hashes, packing = lived(game, years)
    return Lived(game.seed, start, rows, game.outcome or ALIVE, game.tick, hashes, packing)


def lived(game: Game, years: int) -> tuple[list[dict[str, float]], tuple[str, ...], float]:
    """
    A row a year: levels at its last tick, totals over it, the ticks spent in each state, the children who left
    the first stage grown or dead, the cells the band remembers and the size of the snapshot the store would
    keep, in KB; the hash of the state at the end of every year; the mean seconds a snapshot took to pack.
    """
    per_year = game.clock.parts_per_year
    names, columns = game.counters.names, game.unit_columns
    rows: dict[int, dict[str, float]] = {}
    hashes: list[str] = []
    packing: list[float] = []
    before = after = dict(zip(names, game.counters.row(), strict=True))
    row: dict[str, float] = {}
    stages = game.params.units.band.people.stages
    child = next(iter(stages))
    until = stages[child].until
    grows = math.inf if until is None else game.params.days(until)
    while not game.over and game.clock.parts < years * per_year:
        young = [member for member in game.band.members if member.age_days < grows] if game.band else []
        result = game.step()
        year = (result.parts - 1) // per_year + 1
        if year not in rows:
            before = after
            rows[year] = row = dict.fromkeys(YEAR, 0.0) | {'year': year, 'least': math.inf}
        after = dict(zip(names, result.counters, strict=True))
        row.update({name: round(after[counter], 1) for name, counter in LEVELS.items()})
        row.update({name: after[name] - before[name] for name in TOTALS})
        row['growth'] = after['population'] - before['population']
        row['rate'] = round(100 * row['growth'] / before['population'], 1) if before['population'] else 0.0
        row['least'] = min(row['least'], after['population'])
        for unit in result.units:
            for state in dict(zip(columns, unit, strict=True))['state'].split('+'):
                if state in STATES:
                    row[STATES[state]] += 1
        present = {id(member) for member in game.band.members} if game.band else set()
        grown = sum(id(member) in present and member.age_days >= grows for member in young)
        row['grown'] += grown
        row['child-deaths'] += len(young) - grown - after[child]
        for event in result.events:
            if event.key == PEOPLE_BORN:
                row['born'] += event.values['count']
                row['child-deaths'] += event.values['count']
            elif event.key == PEOPLE_LOST:
                cause = f'of-{event.values["cause"]}'
                row[cause] = row.get(cause, 0.0) + event.values['count']
        if result.parts % per_year == 0 or game.over:
            snapshot = game.snapshot()
            began = time.perf_counter()
            packed = pack(snapshot)
            packing.append(time.perf_counter() - began)
            row['known'] = 0 if game.band is None else len(game.band.known)
            row['snapshot'] = round(len(packed) / KB, 1)
            hashes.append(hashed(snapshot))
    return list(rows.values()), tuple(hashes), sum(packing) / len(packing) if packing else 0.0


def hashed(snapshot: dict[str, Any]) -> str:
    """
    The hash of a snapshot but its tree, which a change of the council alone would move.
    """
    return sha256(pack({name: value for name, value in snapshot.items() if name != 'params'})).hexdigest()


def table(years: list[dict[str, float]]) -> list[str]:
    cells = [[_shown(row[name]) for name in YEAR] for row in years]
    widths = [max(len(text) for text in column) for column in zip(YEAR, *cells, strict=True)]
    return ['  '.join(text.rjust(width) for text, width in zip(row, widths, strict=True)) for row in (YEAR, *cells)]


def _shown(value: float) -> str:
    return str(int(value)) if value == int(value) else f'{value:.1f}'


def following(params: Params) -> str:
    """
    What of a tree the life of a band with no player follows from: all of it but the council, of which
    only the spread of the votes, whose leader binds the band, and the status the player starts with count.
    """
    tree = params.tree()
    held = tree['council']
    tree['council'] = {'spread': held['spread'], 'status': {'start': held['status']['start']}}
    return json.dumps(tree, sort_keys=True)


def inputs(params: Params) -> str:
    """
    One hash of all a reference life follows from: the tree, the code of the content, the engine and the planet,
    the codec of the snapshot, this file.
    """
    held = sha256(following(params).encode())
    for path in SOURCES:
        held.update(path.read_bytes())
    return held.hexdigest()


def first_year() -> dict[str, Any]:
    """
    Every seed of FIRST lived one year: the tick each band that died in it died at.
    """
    click.echo(f'  living the first year of {len(FIRST)} seeds', err=True)
    died = {str(seed): life.tick for seed in FIRST if (life := live(seed, 1)).outcome != ALIVE}
    return {'seeds': len(FIRST), 'died': died}


def moved(old: Any, new: Any, path: str = '') -> list[str]:
    """
    Every value that differs between two references, as a line: where, what it was, what it is.
    """
    if isinstance(old, list) and isinstance(new, list):
        old, new = dict(enumerate(old, 1)), dict(enumerate(new, 1))
    if not (isinstance(old, dict) and isinstance(new, dict)):
        return [] if old == new else [f'{path.rstrip(".")}: {old} -> {new}']
    lines = []
    for name in sorted(old.keys() | new.keys(), key=str):
        lines += moved(old.get(name), new.get(name), f'{path}{name}.')
    return lines


@click.command()
@click.argument('path', type=click.Path(dir_okay=False, path_type=Path))
@click.option('--check', is_flag=True, help='Only say whether the reference is the one of this band.')
@click.option('--out', type=click.Path(file_okay=False, path_type=Path), help='Folder for report.txt.')
@click.pass_context
def cli(ctx: click.Context, path: Path, check: bool, out: Path | None) -> None:
    """
    Live every seed of SEEDS for YEARS and of FIRST for one on the default tree,
    rewrite the reference and say what moved.
    """
    params = load_params()
    kept = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'inputs': None, 'seeds': {}}
    if check:
        if kept['inputs'] != inputs(params):
            click.echo(f'the band changed: {len(SEEDS)} seeds are lived {YEARS} years anew, {len(FIRST)} one', err=True)
            ctx.exit(1)
        return

    report: list[str] = []
    found: dict[str, Any] = {}
    for seed in SEEDS:
        began = time.perf_counter()
        life = live(seed, YEARS)
        took = time.perf_counter() - began
        found[str(seed)] = life.data()
        tick, packed = 1000 * took / max(life.tick, 1), 1000 * life.packing
        timed = f'took {took:.1f} s, {tick:.2f} ms a tick, {packed:.1f} ms a pack'
        told = [f'seed {seed}', *life.lines(), timed, '']
        click.echo('\n'.join(told))
        report += told
    began = time.perf_counter()
    first = first_year()
    took = time.perf_counter() - began
    told = [f'first year: {len(first["died"])} of {first["seeds"]} bands died, took {took:.1f} s', '']
    click.echo('\n'.join(told))
    report += told
    held = {'inputs': inputs(params), 'seeds': found, 'first_year': first}
    path.write_text(json.dumps(held, indent=2) + '\n', encoding='utf-8')
    lines = moved(kept['seeds'], found) + moved(kept.get('first_year'), first, 'first_year.')
    told = [f'{path} is rewritten: {len(lines)} values moved', *(f'  {line}' for line in lines)]
    click.echo('\n'.join(told))
    report += told
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / 'report.txt').write_text('\n'.join(report) + '\n', encoding='utf-8')


if __name__ == '__main__':
    cli()
