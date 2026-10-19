"""
The command line of the console client: play or watch a game, review the played ones, or live one headless.
"""

import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import click
import httpx
from websockets.exceptions import WebSocketException

from ..core.errors import DominionError
from ..core.settings import Settings
from ..i18n import FALLBACK, LANGUAGES
from ..runner import lives, record_path
from ..runner import replay as replay_record
from .api import SERVER, Api, Refused
from .lines import words
from .player import Player
from .review import Review
from .screen import PACE_S, Screen
from .session import Session
from .watcher import watch as lines_of

STEP = 'step'
REAL_TIME = 'real-time'
NOISY = ('httpx', 'httpcore', 'websockets', 'asyncio')
POLL_S = 0.2

server_option = click.option('--server', default=SERVER, show_default=True, help='Address of the server.')
review_lang = click.option(
    '--lang', type=click.Choice(LANGUAGES), default=FALLBACK, show_default=True, help='Language of the screen.'
)
records_option = click.option(
    '--records',
    type=click.Path(file_okay=False, path_type=Path),
    default=lambda: Settings().records_dir,
    show_default='DT_RECORDS_DIR',
    help='Directory of the records of played games.',
)


@contextmanager
def _reported(lang: list[str]) -> Iterator[None]:
    try:
        yield
    except Refused as refused:
        raise click.ClickException(words({'key': refused.key, 'values': refused.values}, lang[0])) from refused
    except DominionError as error:
        raise click.ClickException(words(error.message(), lang[0])) from error
    except (httpx.HTTPError, WebSocketException, OSError) as error:
        raise click.ClickException(str(error)) from error


def _awaited(api: Api, seconds: float) -> None:
    """
    Ask the server's health until it answers or the seconds run out; the last failure is raised.
    """
    deadline = time.monotonic() + seconds
    while True:
        try:
            api.health()
            return
        except httpx.TransportError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(POLL_S)


def _overrides(given: tuple[str, ...]) -> dict[str, Any]:
    read: dict[str, Any] = {}
    for item in given:
        path, found, value = item.partition('=')
        if not path or not found:
            raise click.BadParameter(f'{item} is not PATH=VALUE', param_hint='--set')
        try:
            read[path] = json.loads(value)
        except ValueError:
            read[path] = value
    return read


@click.group()
def cli() -> None:
    """
    The console client of Dominion Theory.
    """
    # core sets the root logger to DEBUG, which would print every request between the lines.
    for name in NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)


@cli.command()
@server_option
@click.option('--game', 'game_id', help='Join this game instead of creating one.')
@click.option('--lang', type=click.Choice(LANGUAGES), help='Language of the lines; the one of the profile if left out.')
@click.option('--step', is_flag=True, help='Play in step mode and answer every wait with pass.')
@click.option('--updates', 'limit', type=click.IntRange(min=1), help='Stop after this many updates.')
@click.option('--seed', type=click.IntRange(min=0), help='Seed of a new game.')
@click.option('--preset', help='Preset of a new game.')
@click.option('--set', 'given', multiple=True, metavar='PATH=VALUE', help='Override one parameter of a new game.')
def watch(
    server: str,
    game_id: str | None,
    lang: str | None,
    step: bool,
    limit: int | None,
    seed: int | None,
    preset: str | None,
    given: tuple[str, ...],
) -> None:
    """
    Print every update of a game as a line: its date and the words of its events.
    """
    overrides = _overrides(given)
    tongue = [lang or FALLBACK]
    with closing(Api(server)) as api, _reported(tongue):
        tongue[0] = lang or api.language()
        if game_id is None:
            game = api.create(STEP if step else REAL_TIME, seed, preset, overrides)
        else:
            game = api.game(game_id)
        click.echo(f'game {game["id"]}', err=True)
        run = game_id is None and game['mode'] == REAL_TIME
        for line in lines_of(api, game['id'], tongue[0], step, limit, run):
            click.echo(line)


@cli.command()
@server_option
@click.option('--lang', type=click.Choice(LANGUAGES), help='Language of the game; the one of the profile if left out.')
@click.option('--updates', 'limit', type=click.IntRange(min=1), help='Stop after this many updates.')
@click.option('--seed', type=click.IntRange(min=0), help='Seed of the game.')
@click.option('--preset', help='Preset of the game.')
@click.option('--set', 'given', multiple=True, metavar='PATH=VALUE', help='Override one parameter of the game.')
@click.option('--debug', is_flag=True, help="After every update, the band's cell, what moved in it and the reason.")
@click.option('--wait', type=click.FloatRange(min=0), default=0, help='Seconds to wait for the server to come up.')
@click.option('--pace', type=click.FloatRange(min=0), default=PACE_S, help='Seconds between ticks on the screen.')
def play(
    server: str,
    lang: str | None,
    limit: int | None,
    seed: int | None,
    preset: str | None,
    given: tuple[str, ...],
    debug: bool,
    wait: float,
    pace: float,
) -> None:
    """
    Play a band in step mode: in a terminal a screen with the map, the band, the council and the log;
    otherwise a coloured line per update, and the map and a numbered list at every council.
    """
    overrides = _overrides(given)
    tongue = [lang or FALLBACK]
    with closing(Api(server)) as api, _reported(tongue):
        _awaited(api, wait)
        tongue[0] = lang or api.language()
        game = api.create(STEP, seed, preset, overrides, seated=True)
        click.echo(f'game {game["id"]}', err=True)
        if sys.stdin.isatty() and sys.stdout.isatty():
            failed = Screen(Session(api, game['id']), tongue[0], debug, pace, limit).run()
            if failed:
                raise click.ClickException(failed)
            return
        try:
            for line in Player(api, game['id'], tongue[0], debug=debug).lines(limit):
                click.echo(line)
        except click.Abort, KeyboardInterrupt, EOFError:
            click.echo(err=True)


@cli.group()
def replay() -> None:
    """
    Played games: list them, play one back on the screen, or check that its record replays.
    """


@replay.command('list')
@records_option
@review_lang
def listed(records: Path, lang: str) -> None:
    """
    The played games of the records directory with a summary each; Enter plays one back.
    """
    Review(records, lang).run()


@replay.command('play')
@records_option
@review_lang
@click.argument('game_id')
def played_back(records: Path, lang: str, game_id: str) -> None:
    """
    Play a game back from its record: the planet, the window and the trail, the panes, the log and charts.
    """
    if not record_path(records, game_id).exists():
        raise click.ClickException(f'no record of {game_id} in {records}')
    Review(records, lang, game_id).run()


@replay.command('check')
@server_option
@click.argument('game_id')
def check(server: str, game_id: str) -> None:
    """
    Download the record of a game and say whether it replays with every hash matching.
    """
    with closing(Api(server)) as api, _reported([FALLBACK]), TemporaryDirectory() as folder:
        path = Path(folder) / f'{game_id}.jsonl.gz'
        path.write_bytes(api.record(game_id))
        played = replay_record(path)
    if not played.matched:
        raise click.ClickException(f'the record of {game_id} diverges at tick {played.diverged_at}')
    click.echo(f'the record of {game_id} replays: {played.game.tick} ticks, every hash matches')


cli.add_command(replay, 'replays')


@cli.command()
@click.option('--years', type=click.IntRange(min=1), default=lives.YEARS, show_default=True, help='Years to live.')
@click.option('--seed', type=click.IntRange(min=0), help='Seed of the game; a random one if left out.')
@click.option('--preset', help='Preset of the game.')
@click.option('--set', 'given', multiple=True, metavar='PATH=VALUE', help='Override one parameter of the game.')
def live(years: int, seed: int | None, preset: str | None, given: tuple[str, ...]) -> None:
    """
    Live a game with no player and no server, and print a row per year from its counters.
    """
    with _reported([FALLBACK]):
        life = lives.live(seed, years, preset, _overrides(given))
    click.echo(f'seed {life.seed}', err=True)
    for text in life.lines():
        click.echo(text)
