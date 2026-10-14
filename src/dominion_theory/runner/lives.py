"""
A band lived headless, with no player and no server, as a row a year from its counters; and the lives
of a few seeds kept in a file, so that a change of how a band lives is seen.
"""

import json
import math
import secrets
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import click

from ..content import Params, load_params
from ..engine import Game
from ..engine.events import PEOPLE_BORN, PEOPLE_LOST
from .service import SEED_BITS

SEEDS = (1, 2, 3, 4, 5)
YEARS = 10
# The size at which a band becomes a tribe, from the notes of stage 5 in docs/roadmap.md; not a rule yet.
TRIBE = 150
ALIVE = 'alive'
PACKAGE = Path(__file__).parents[1]
SOURCES = (Path(__file__), *(path for name in ('engine', 'planet') for path in sorted((PACKAGE / name).glob('*.py'))))
LEVELS = {'people': 'population', 'food': 'food', 'water': 'water', 'status': 'status'}
TOTALS = ('deaths', 'moves', 'gathers', 'camps', 'encounters')
STATES = {'starvation': 'starving', 'thirst': 'thirsty', 'tiredness': 'tired'}
CAUSES = ('hunger', 'thirst', 'encounter')
YEAR = (
    'year',
    'people',
    'growth',
    'rate',
    'least',
    'born',
    'deaths',
    *(f'of-{cause}' for cause in CAUSES),
    'food',
    'water',
    'moves',
    'gathers',
    'camps',
    *STATES.values(),
    'encounters',
    'status',
)


@dataclass(frozen=True)
class Lived:
    seed: int
    start: int
    years: list[dict[str, float]]
    outcome: str
    tick: int

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
        }

    def lines(self) -> list[str]:
        growth, tribe = self.growth, self.tribe
        grew = 'no growth' if growth is None else f'grows {growth:.1%} a year'
        reached = f'{TRIBE} people never' if tribe is None else f'{TRIBE} people in year {math.ceil(tribe)}'
        return [*table(self.years), f'{self.outcome} at tick {self.tick}: {grew}, {reached}']


def live(seed: int | None, years: int, preset: str | None = None, overrides: dict[str, Any] | None = None) -> Lived:
    params = load_params(preset, overrides)
    game = Game.create(seed=secrets.randbits(SEED_BITS) if seed is None else seed, params=params)
    start = 0 if game.band is None else game.band.population
    rows = lived(game, years)
    return Lived(game.seed, start, rows, game.outcome or ALIVE, game.tick)


def lived(game: Game, years: int) -> list[dict[str, float]]:
    """
    A row a year: levels at its last tick, totals over it, the ticks spent in each state.
    """
    per_year = game.clock.parts_per_year
    names, columns = game.counters.names, game.unit_columns
    rows: dict[int, dict[str, float]] = {}
    before = after = dict(zip(names, game.counters.row(), strict=True))
    row: dict[str, float] = {}
    while not game.over and game.clock.parts < years * per_year:
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
        for event in result.events:
            if event.key == PEOPLE_BORN:
                row['born'] += event.values['count']
            elif event.key == PEOPLE_LOST:
                cause = f'of-{event.values["cause"]}'
                row[cause] = row.get(cause, 0.0) + event.values['count']
    return list(rows.values())


def table(years: list[dict[str, float]]) -> list[str]:
    cells = [[_shown(row[name]) for name in YEAR] for row in years]
    widths = [max(len(text) for text in column) for column in zip(YEAR, *cells, strict=True)]
    return ['  '.join(text.rjust(width) for text, width in zip(row, widths, strict=True)) for row in (YEAR, *cells)]


def _shown(value: float) -> str:
    return str(int(value)) if value == int(value) else f'{value:.1f}'


def following(params: Params) -> str:
    """
    What of a tree the life of a band with no player follows from: all of it but the council.
    """
    tree = params.tree()
    tree.pop('council')
    return json.dumps(tree, sort_keys=True)


def inputs(params: Params) -> str:
    """
    One hash of all a reference life follows from: the tree, the code of the engine and of the planet, this file.
    """
    held = sha256(following(params).encode())
    for path in SOURCES:
        held.update(path.read_bytes())
    return held.hexdigest()


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
    Live every seed of SEEDS for YEARS on the default tree, rewrite the reference and say what moved.
    """
    params = load_params()
    kept = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'inputs': None, 'seeds': {}}
    if check:
        if kept['inputs'] != inputs(params):
            click.echo(f'the band changed: {len(SEEDS)} seeds are lived {YEARS} years anew', err=True)
            ctx.exit(1)
        return

    report: list[str] = []
    found: dict[str, Any] = {}
    for seed in SEEDS:
        life = live(seed, YEARS)
        found[str(seed)] = life.data()
        told = [f'seed {seed}', *life.lines(), '']
        click.echo('\n'.join(told))
        report += told
    path.write_text(json.dumps({'inputs': inputs(params), 'seeds': found}, indent=2) + '\n', encoding='utf-8')
    lines = moved(kept['seeds'], found)
    told = [f'{path} is rewritten: {len(lines)} values moved', *(f'  {line}' for line in lines)]
    click.echo('\n'.join(told))
    report += told
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / 'report.txt').write_text('\n'.join(report) + '\n', encoding='utf-8')


if __name__ == '__main__':
    cli()
