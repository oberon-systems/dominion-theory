"""
make batch: the games of a run file played by workers into lab/<moment>-<name>/, a line of summary.jsonl a game
and report.txt rewritten as games end, docs/lab/runs.md.
"""

import json
import multiprocessing
import shutil
import time
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime
from functools import partial
from pathlib import Path
from statistics import median
from typing import Any

import click

from ..core.settings import Settings, get_settings
from ..players import SEAT, made, sit
from ..runner import CAP, DIED, REACHED, STEP, Service, Tally
from .report import Line, growth, report
from .run import Planned, Run, load

LAB = Path('lab')
RUN = 'run.yaml'
SUMMARY = 'summary.jsonl'
REPORT = 'report.txt'
MOMENT = '%Y%m%d-%H%M'


def play(planned: Planned, run: Run, settings: Settings) -> Line:
    """
    One game in step mode by the runner of the server, the seat answered by the player at every council and the
    rest passed, until the goal, the cap of years, death or banishment; its record kept only for the first draws.
    """
    began = time.perf_counter()
    held = run.params[planned.set]
    service = Service(settings=settings.model_copy(update={'store_url': ''}))
    runner = service.create(
        seed=planned.land,
        preset=held.preset,
        overrides=held.overrides,
        mode=STEP,
        seats={SEAT: planned.player},
        seated=True,
        draw=planned.draw,
    )
    game = runner.game
    player = made(run.spec(planned.player), game.params, planned.land, planned.draw)
    tally = Tally(game)
    runner.subscribe(tally.heard)
    cap = round(run.until.years * game.clock.parts_per_year)
    outcome = None
    while not runner.ended:
        if tally.people >= run.until.people:
            outcome = REACHED
        elif game.clock.parts >= cap:
            outcome = CAP
        if outcome is not None:
            runner.end(outcome)
            break
        asked = sit(game, player, runner.submit)
        if asked is None or asked[1] is None:
            runner.step()
    kept = planned.draw < run.records
    if not kept:
        runner.record_path.unlink(missing_ok=True)
    return {
        **planned.data(),
        'outcome': outcome or game.outcome,
        **tally.data(),
        'record': runner.id if kept else None,
        'seconds': round(time.perf_counter() - began, 1),
    }


def played(lines: Iterable[Line]) -> set[tuple[int, int, str, str]]:
    return {(line['land'], line['draw'], line['player'], line['set']) for line in lines}


def read(path: Path) -> list[Line]:
    if not path.exists():
        return []
    return [json.loads(text) for text in path.read_text(encoding='utf-8').splitlines() if text.strip()]


def _games(run: Run, left: list[Planned], settings: Settings) -> Iterator[Line]:
    playing = partial(play, run=run, settings=settings)
    if run.workers == 1 or len(left) <= 1:
        yield from map(playing, left)
        return
    with multiprocessing.get_context('spawn').Pool(min(run.workers, len(left))) as pool:
        yield from pool.imap_unordered(playing, left)


def _told(run: Run, group: list[Line], days: int) -> str:
    first = group[0]
    reached = sum(line['outcome'] == REACHED for line in group)
    early = sum(line['outcome'] == DIED and line['day'] < days for line in group)
    grew = [held for line in group if (held := growth(line, days)) is not None]
    shown = f'{median(grew):+.1%}' if grew else '-'
    return (
        f'land {first["land"]}, {first["player"]}, {first["set"]}: {len(group)} games, '
        f'{reached} reached {run.until.people}, growth {shown}, {early} died in the first year'
    )


def batch(
    run: Run, name: str, out: Path, settings: Settings | None = None, echo: Callable[[str], Any] = click.echo
) -> list[Line]:
    """
    Plays the games of the run that the summary in out does not hold yet; the lines of every game in the end.
    """
    settings = settings or get_settings()
    planned = run.planned()
    summary, written = out / SUMMARY, out / REPORT
    lines = read(summary)
    done = played(lines)
    left = [held for held in planned if held.key not in done]
    days = {held: params.params().time.days_per_year for held, params in run.params.items()}
    sizes = Counter((held.land, held.player, held.set) for held in planned)
    echo(
        f'{name}: {len(run.seeds)} lands, {run.draws} draws, {len(run.seated)} players, {len(run.params)} sets: '
        f'{len(planned)} games, {len(left)} to play, {run.workers} workers'
    )
    written.write_text('\n'.join(report(name, run, lines, days, len(planned))) + '\n', encoding='utf-8')
    with summary.open('a', encoding='utf-8') as file:
        for line in _games(run, left, settings):
            file.write(json.dumps(line) + '\n')
            file.flush()
            lines.append(line)
            written.write_text('\n'.join(report(name, run, lines, days, len(planned))) + '\n', encoding='utf-8')
            group = [held for held in lines if (held['land'], held['player'], held['set']) == _group(line)]
            if len(group) == sizes[_group(line)]:
                echo(_told(run, group, days[line['set']]))
    return lines


def _group(line: Line) -> tuple[int, str, str]:
    return line['land'], line['player'], line['set']


@click.command()
@click.argument('path', required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    '--resume',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help='A run directory cut short: only the games its summary lacks are played.',
)
@click.option('--out', type=click.Path(file_okay=False, path_type=Path), default=LAB, help='Where the run goes.')
def cli(path: Path | None, resume: Path | None, out: Path) -> None:
    """
    Play the games of the run file PATH into OUT/<moment>-<name>/.
    """
    if resume is not None:
        folder = resume
        name = folder.name.split('-', 2)[-1]
    elif path is not None:
        name = path.stem
        folder = out / f'{datetime.now().strftime(MOMENT)}-{name}'
        folder.mkdir(parents=True)
        shutil.copyfile(path, folder / RUN)
    else:
        raise click.UsageError('a run file, or --resume with a run directory')
    batch(load(folder / RUN), name, folder)


if __name__ == '__main__':
    cli()
