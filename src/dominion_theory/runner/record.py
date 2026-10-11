"""
The run record of docs/architecture/records.md: its lines, the writer and the replay.
"""

import gzip
import json
import zlib
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

from ..content import Params
from ..core.errors import DominionError
from ..engine import Command, Game, StepResult

FORMAT = 1
SUFFIX = '.jsonl.gz'
HEADER = 'header'
COMMAND = 'command'
TICK = 'tick'
EVENT = 'event'
FOOTER = 'footer'
PERSON = 'person'
RECORD_UNREADABLE = 'error-record-unreadable'

type Line = dict[str, Any]
type Judged = tuple[int, Command, bool]


def record_path(directory: Path, game_id: str) -> Path:
    return directory / f'{game_id}{SUFFIX}'


def header_line(game_id: str, game: Game, kinds: dict[str, str] | None = None) -> Line:
    return {
        't': HEADER,
        'format': FORMAT,
        'engine': version('dominion-theory'),
        'game': game_id,
        'seed': game.seed,
        'params_hash': game.params.hash,
        'params': game.params.tree(),
        'seats': [{'seat': seat, 'kind': (kinds or {}).get(seat, PERSON)} for seat in game.seats],
        'counters': list(game.counters.names),
        'units': list(game.unit_columns),
    }


def tick_lines(result: StepResult, judged: list[Judged]) -> list[Line]:
    lines: list[Line] = [
        {
            't': COMMAND,
            'tick': result.tick,
            'seat': command.seat,
            'seq': seq,
            'command': command.envelope(),
            'accepted': accepted,
        }
        for seq, command, accepted in judged
    ]
    lines.append(
        {
            't': TICK,
            'tick': result.tick,
            'parts': result.parts,
            'hash': result.hash,
            'counters': result.counters,
            'units': result.units,
        }
    )
    lines.extend({'t': EVENT, 'tick': result.tick, **event.data()} for event in result.events)
    return lines


def footer_line(outcome: str, tick: int, hash: str) -> Line:
    return {'t': FOOTER, 'outcome': outcome, 'tick': tick, 'hash': hash}


def _members(data: bytes) -> tuple[list[Line], int]:
    lines: list[Line] = []
    view = memoryview(data)
    size = 0
    while size < len(data):
        member = zlib.decompressobj(wbits=31)
        try:
            text = member.decompress(view[size:])
        except zlib.error:
            break
        # A member cut short is a day that was never fully written: none of it is kept.
        if not member.eof:
            break
        lines.extend(json.loads(line) for line in text.splitlines())
        size = len(data) - len(member.unused_data)
    return lines, size


def read(path: str | Path) -> list[Line]:
    return _members(Path(path).read_bytes())[0]


class RecordWriter:
    """
    Collects lines and writes them out as one gzip member per call of flush.
    """

    def __init__(self, path: Path, header: Line) -> None:
        self.path = path
        self._lines: list[Line] = []
        held, size = _members(path.read_bytes()) if path.exists() else ([], 0)
        self.last = max((line['tick'] for line in held if line.get('t') == TICK), default=0)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('r+b' if held else 'wb') as file:
            file.truncate(size)
        if not held:
            self._lines.append(header)
            self.flush()

    def add(self, tick: int, lines: list[Line]) -> None:
        # A restored game steps again through ticks the file may already hold.
        if tick > self.last:
            self.last = tick
            self._lines.extend(lines)

    def flush(self) -> None:
        if not self._lines:
            return
        text = ''.join(json.dumps(line, separators=(',', ':')) + '\n' for line in self._lines)
        with self.path.open('ab') as file:
            file.write(gzip.compress(text.encode(), mtime=0))
        self._lines.clear()

    def close(self, footer: Line) -> None:
        self._lines.append(footer)
        self.flush()


@dataclass(frozen=True)
class Replay:
    matched: bool
    diverged_at: int | None
    game: Game


def replay(path: str | Path, params: Params | None = None) -> Replay:
    """
    Plays a record again. Other parameters than the header's may be given, to compare the two.
    """
    lines = read(path)
    if not lines or lines[0].get('t') != HEADER or lines[0].get('format') != FORMAT:
        raise DominionError(RECORD_UNREADABLE, path=str(path))
    header = lines[0]
    game = Game.create(seed=header['seed'], params=params or Params.model_validate(header['params']))
    diverged_at = None
    for line in lines[1:]:
        kind = line.get('t')
        if kind == COMMAND:
            game.submit(Command.read(line['seat'], line['command']))
        elif kind == TICK and game.step().hash != line['hash'] and diverged_at is None:
            diverged_at = line['tick']
    return Replay(diverged_at is None, diverged_at, game)
