"""
Watching a game: join the stream right after the snapshot and give out a line per update.
"""

from collections.abc import Iterator
from contextlib import closing, suppress

from .api import Api, Refused
from .lines import line

PASS = 'pass'  # noqa: S105


def _answer(api: Api, game_id: str, seq: int) -> None:
    api.command(game_id, {'id': f'{PASS}-{seq}', 'kind': PASS})


def watch(
    api: Api,
    game_id: str,
    lang: str,
    step: bool = False,
    limit: int | None = None,
    run: bool = False,
) -> Iterator[str]:
    """
    The lines of a game, at most limit of them. With step, every wait is answered with pass;
    with run, the clock is started once the snapshot is read and stopped when the watch ends.
    """
    snapshot = api.snapshot(game_id)
    if step and snapshot['waiting']:
        _answer(api, game_id, snapshot['seq'])
    if run:
        api.clock(game_id, 'resume')
    seen = 0
    try:
        with closing(api.updates(game_id, snapshot['seq'])) as stream:
            for message in stream:
                if message.get('resync'):
                    waiting = api.snapshot(game_id)['waiting']
                else:
                    yield line(message, lang)
                    seen += 1
                    if seen == limit:
                        return
                    waiting = message['waiting']
                if step and waiting:
                    _answer(api, game_id, message['seq'])
    finally:
        if run:
            with suppress(Refused):
                api.clock(game_id, 'pause')
