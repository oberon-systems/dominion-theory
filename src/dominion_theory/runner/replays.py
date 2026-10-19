"""
The records of played games read back without playing them again: a summary of each, and the frames of one, a
frame per tick, to show it on a screen. The engine moves on while records stay, so nothing here steps a game.
"""

import json
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..content import Params, load_params
from ..core.errors import DominionError
from ..engine import Lands, lands
from ..engine.clock import Clock
from .record import BAND, COMMAND, EVENT, FOOTER, FORMAT, HEADER, MEMBERS, RECORD_UNREADABLE, SUFFIX, TICK, Line, read

UNFINISHED = 'unfinished'
UNREADABLE = 'unreadable'
BORN = 'people-born'
# The columns of the planet drawn beside the window.
ACROSS = 240


@dataclass(frozen=True)
class Summary:
    """
    One played game in a line: who played, how long, how it ended and what the band came to.
    """

    game: str
    path: Path
    written: int
    seed: int | None = None
    seated: bool = False
    ticks: int = 0
    days: int = 0
    outcome: str = UNREADABLE
    start: int = 0
    end: int = 0
    most: int = 0
    born: int = 0
    died: int = 0
    skills: int = 0
    status: float | None = None
    days_a_year: int = 1


@dataclass(frozen=True)
class Frame:
    """
    One tick of a record: its date, counters by name, the band's row, the band and members as last written,
    and what happened.
    """

    tick: int
    parts: int
    date: dict[str, Any]
    counters: dict[str, float]
    row: dict[str, Any] | None
    band: dict[str, Any] | None
    members: list[dict[str, Any]] | None
    events: list[dict[str, Any]]
    votes: list[dict[str, Any]]


@dataclass(frozen=True)
class Played:
    """
    A record read whole: its summary, the tree it is drawn by, whether that is the tree it was played by, the
    frames and the land.
    """

    summary: Summary
    params: Params
    exact: bool
    frames: list[Frame]
    lands: Lands


def summaries(directory: Path) -> list[Summary]:
    """
    Every record of a directory, the latest written first.
    """
    found = [summary(path) for path in directory.glob(f'*{SUFFIX}')] if directory.is_dir() else []
    return sorted(found, key=lambda held: (-held.written, held.game))


def summary(path: Path) -> Summary:
    game, written = path.name.removesuffix(SUFFIX), int(path.stat().st_mtime)
    lines = _lines(path)
    if lines is None:
        return Summary(game, path, written)
    header = lines[0]
    names = header['counters']
    ticks = [line for line in lines if line.get('t') == TICK]
    people = [_counted(names, line, 'population') for line in ticks]
    last = ticks[-1] if ticks else None
    footer = next((line for line in reversed(lines) if line.get('t') == FOOTER), None)
    calendar = header['params']['time']
    per_day = len(calendar['day_parts'])
    days_a_year = calendar['days_per_month'] * sum(season['months'] for season in calendar['seasons'])
    born = sum(line['values'].get('count', 0) for line in lines if line.get('t') == EVENT and line['key'] == BORN)
    return Summary(
        game=game,
        path=path,
        written=written,
        seed=header['seed'],
        seated=header['seated'],
        ticks=0 if last is None else last['tick'],
        days=0 if last is None else last['parts'] // per_day,
        outcome=UNFINISHED if footer is None else footer['outcome'],
        start=int(people[0]) if people else 0,
        end=int(people[-1]) if people else 0,
        most=int(max(people, default=0)),
        born=int(born),
        died=0 if last is None else int(_counted(names, last, 'deaths')),
        skills=0 if last is None else int(_counted(names, last, 'skills')),
        status=None if last is None or not header['seated'] else _counted(names, last, 'status'),
        days_a_year=days_a_year,
    )


def played(path: Path, across: int = ACROSS) -> Played:
    """
    The frames of a record, a frame per tick, and its land drawn again from the seed.
    """
    lines = _lines(path)
    if lines is None:
        raise DominionError(RECORD_UNREADABLE, path=str(path))
    header = lines[0]
    params, exact = _params(header['params'])
    names, columns = header['counters'], header['units']
    frames: list[Frame] = []
    band: dict[str, Any] | None = None
    members: list[dict[str, Any]] | None = None
    votes: list[dict[str, Any]] = []
    for line in lines[1:]:
        kind = line.get('t')
        if kind == COMMAND:
            votes.append(line['command'])
        elif kind == EVENT and frames and line['tick'] == frames[-1].tick:
            frames[-1].events.append({'key': line['key'], 'values': line.get('values', {})})
        elif kind == TICK:
            band = line.get(BAND, band)
            members = line.get(MEMBERS, members)
            rows = line['units']
            row = dict(zip(columns, rows[0], strict=True)) if rows else None
            date = asdict(Clock(params.time, line['parts']).date)
            counted = dict(zip(names, line['counters'], strict=True))
            frames.append(Frame(line['tick'], line['parts'], date, counted, row, band, members, [], votes))
            votes = []
    return Played(summary(path), params, exact, frames, lands(header['seed'], params, across))


def _lines(path: Path) -> list[Line] | None:
    try:
        lines = read(path)
    except OSError, EOFError, zlib.error, json.JSONDecodeError:
        return None
    if not lines or lines[0].get('t') != HEADER or lines[0].get('format') != FORMAT:
        return None
    return lines


def _counted(names: list[str], line: Line, name: str) -> float:
    return float(line['counters'][names.index(name)]) if name in names else 0.0


def _params(tree: dict[str, Any]) -> tuple[Params, bool]:
    """
    The tree a record was played by; when the schema has moved past it, the defaults with its planet, so the
    land is still the one played on, or the defaults alone.
    """
    try:
        return Params.model_validate(tree), True
    except ValueError:
        pass
    try:
        return load_params(overrides={'planet': tree['planet']}), False
    except DominionError, KeyError:
        return load_params(), False
