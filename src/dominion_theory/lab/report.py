"""
The tables of report.txt from the lines of summary.jsonl, docs/lab/metrics.md.
"""

import math
from collections.abc import Callable, Iterable
from statistics import median
from typing import Any

from ..players import Leader
from ..runner import BANISHED, DIED, REACHED
from .run import Run

type Line = dict[str, Any]

COLUMNS = (
    'games',
    'reached',
    'time',
    'growth',
    'projected',
    'early',
    'lost',
    'turned',
    'worked',
    'gain',
    'gain-growth',
)
NONE = '-'


def growth(line: Line, days: int) -> float | None:
    """
    The yearly growth of a band still living and short of the goal, compounded over the years it lived.
    """
    people = line['people']
    if line['outcome'] in (REACHED, DIED, BANISHED) or line['day'] <= 0 or min(people['start'], people['end']) <= 0:
        return None
    return float((people['end'] / people['start']) ** (days / line['day']) - 1)


def _share(count: float, of: float) -> str:
    return NONE if of <= 0 else f'{count / of:.1%}'


def _summed(lines: list[Line], field: str, name: str) -> int:
    return sum(line[field][name] for line in lines)


def _land(line: Line) -> tuple[int, int]:
    return line['land'], line['draw']


class Measures:
    """
    The measures of a group of games played under one set of parameters, a day of the year being days.
    """

    def __init__(self, lines: list[Line], days: int, goal: int) -> None:
        self.lines, self.days, self.goal = lines, days, goal

    @property
    def reached(self) -> float:
        return sum(1 for line in self.lines if line['outcome'] == REACHED) / len(self.lines)

    @property
    def growth(self) -> float | None:
        found = [held for line in self.lines if (held := growth(line, self.days)) is not None]
        return median(found) if found else None

    def gain(self, leader: Measures) -> list[str]:
        """
        What these games reached and grew by beyond the leader's on the same lands and draws.
        """
        mine, theirs = self.growth, leader.growth
        grew = NONE if mine is None or theirs is None else f'{mine - theirs:+.1%}'
        return [f'{self.reached - leader.reached:+.1%}', grew]

    def row(self) -> list[str]:
        lines = self.lines
        reached = [line['day'] for line in lines if line['outcome'] == REACHED]
        grew, start = self.growth, median(line['people']['start'] for line in lines)
        projected = NONE
        if grew is not None and grew > 0 and start > 0:
            projected = str(math.ceil(max(math.log(self.goal / start) / math.log(1 + grew), 0.0)))
        early = sum(line['outcome'] == DIED and line['day'] < self.days for line in lines)
        lost = sum(line['outcome'] in (DIED, BANISHED) for line in lines)
        verdicts = sum(sum(line['verdicts'].values()) for line in lines)
        return [
            str(len(lines)),
            f'{self.reached:.1%}',
            str(round(median(reached))) if reached else NONE,
            NONE if grew is None else f'{grew:+.1%}',
            projected,
            _share(early, len(lines)),
            _share(lost, len(lines)),
            _share(_summed(lines, 'councils', 'turned'), _summed(lines, 'councils', 'sat')),
            _share(_summed(lines, 'verdicts', 'worked'), verdicts),
        ]


def table(head: Iterable[str], rows: list[list[str]]) -> list[str]:
    """
    The first column to the left, the others to the right.
    """
    cells = [list(head), *rows]
    widths = [max(len(row[column]) for row in cells) for column in range(len(cells[0]))]
    return [
        '  '.join(
            text.ljust(width) if column == 0 else text.rjust(width)
            for column, (text, width) in enumerate(zip(row, widths, strict=True))
        )
        for row in cells
    ]


def _players(run: Run, lines: list[Line]) -> list[str]:
    played = {line['player'] for line in lines}
    return [name for name, _, _ in run.seated if name in played]


def _measured(run: Run, lines: list[Line], days: int, prefix: str = '') -> list[list[str]]:
    """
    A row per player; its gain over the leader is taken on the lands and draws both played.
    """
    goal = run.until.people
    led = {_land(line): line for line in lines if line['player'] == Leader.name}
    rows = []
    for name in _players(run, lines):
        held = [line for line in lines if line['player'] == name]
        both = [line for line in held if _land(line) in led]
        gain = [NONE, NONE]
        if name != Leader.name and both:
            gain = Measures(both, days, goal).gain(Measures([led[_land(line)] for line in both], days, goal))
        rows.append([f'{prefix}{name}', *Measures(held, days, goal).row(), *gain])
    return rows


def _shares(
    run: Run, lines: list[Line], names: list[str], count: Callable[[Line, str], float], shown: Callable[[float], str]
) -> list[list[str]]:
    """
    A row per name, a column per player: the mean count of the name in its games.
    """
    by = {player: [line for line in lines if line['player'] == player] for player in _players(run, lines)}
    rows = []
    for name in names:
        rows.append([name, *(shown(sum(count(line, name) for line in held) / len(held)) for held in by.values())])
    return rows


def _learned(line: Line, skill: str) -> float:
    return float(skill in line['skills'])


def _died(line: Line, cause: str) -> float:
    return float(line['causes'].get(cause, 0))


def _called(line: Line, occasion: str) -> float:
    return float(line['occasions'].get(occasion, 0))


def _named(lines: list[Line], field: str) -> list[str]:
    return sorted({name for line in lines for name in line[field]})


def report(name: str, run: Run, lines: list[Line], days: dict[str, int], total: int) -> list[str]:
    """
    Per set of parameters: a row per player, the same per land, then the skills learned as a share of the games,
    the deaths by cause and the councils by occasion as the mean of a game.
    """
    told = [f'{name}: {len(lines)} of {total} games', '']
    for held in run.params:
        played = [line for line in lines if line['set'] == held]
        if not played:
            continue
        per, players = days[held], _players(run, played)
        told += [*table((held, *COLUMNS), _measured(run, played, per)), '']
        by_land: list[list[str]] = []
        for land in run.seeds:
            on = [line for line in played if line['land'] == land]
            if on:
                by_land += _measured(run, on, per, f'land {land} ')
        told += [*table((f'{held} by land', *COLUMNS), by_land), '']
        mean = '{:.1f}'.format
        for head, field, count, shown in (
            ('learned', 'skills', _learned, '{:.0%}'.format),
            ('died of, a game', 'causes', _died, mean),
            ('councils for, a game', 'occasions', _called, mean),
        ):
            told += [*table((head, *players), _shares(run, played, _named(played, field), count, shown)), '']
    return told
