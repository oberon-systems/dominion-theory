from collections.abc import Generator
from typing import Any

from dominion_theory.client import Api, watch

type Body = dict[str, Any]

DATE = {'year': 1, 'month': 1, 'day': 1, 'part': 'midday', 'season': 'spring'}
SEAT = ['player']


def update(seq: int, waiting: list[str] | None = None) -> Body:
    return {'seq': seq, 'date': DATE, 'events': [], 'changes': {}, 'waiting': waiting or []}


class Scripted(Api):
    """
    Answers from a script instead of a server, and keeps what it was sent.
    """

    def __init__(self, messages: list[Body], waiting: list[str] | None = None) -> None:
        super().__init__()
        self.messages = messages
        self.waiting = waiting or []
        self.sent: list[str] = []
        self.clocked: list[str] = []
        self.joined: list[int] = []
        self.snapshots = 0

    def snapshot(self, game_id: str) -> Body:
        self.snapshots += 1
        return {'seq': 3, 'waiting': self.waiting}

    def command(self, game_id: str, envelope: Body) -> Body:
        assert envelope['kind'] == 'pass'
        self.sent.append(envelope['id'])
        return {'id': envelope['id'], 'taken': True}

    def clock(self, game_id: str, action: str) -> Body:
        self.clocked.append(action)
        return {}

    def updates(self, game_id: str, after: int) -> Generator[Body]:
        self.joined.append(after)
        yield from self.messages


def test_the_stream_is_joined_after_the_snapshot_and_every_update_is_a_line() -> None:
    api = Scripted([update(4), update(5)])

    lines = list(watch(api, 'alpha', 'en'))

    assert api.joined == [3]
    assert lines == ['midday, day 1, month 1, year 1, spring'] * 2
    assert api.sent == []


def test_a_watcher_that_does_not_step_leaves_a_waiting_game_alone() -> None:
    api = Scripted([update(4, SEAT)], SEAT)

    assert len(list(watch(api, 'alpha', 'en'))) == 1
    assert api.sent == []


def test_step_answers_every_wait_with_a_pass_named_by_the_update() -> None:
    api = Scripted([update(4, SEAT), update(5), update(6, SEAT)], SEAT)

    lines = list(watch(api, 'alpha', 'ru', step=True))

    assert len(lines) == 3
    assert api.sent == ['pass-3', 'pass-4', 'pass-6']


def test_the_limit_stops_the_watch_and_the_last_wait_is_not_answered() -> None:
    api = Scripted([update(4, SEAT), update(5, SEAT), update(6, SEAT)], SEAT)

    lines = list(watch(api, 'alpha', 'en', step=True, limit=2))

    assert len(lines) == 2
    assert api.sent == ['pass-3', 'pass-4']


def test_a_resync_is_no_line_and_the_snapshot_is_read_again() -> None:
    api = Scripted([{'resync': True, 'seq': 9}, update(10)], SEAT)

    lines = list(watch(api, 'alpha', 'en', step=True))

    assert len(lines) == 1
    assert api.snapshots == 2
    assert api.sent == ['pass-3', 'pass-9']


def test_a_game_that_is_run_is_resumed_after_the_snapshot_and_paused_at_the_end() -> None:
    api = Scripted([update(4), update(5)])

    lines = watch(api, 'alpha', 'en', run=True, limit=1)

    assert api.clocked == []
    assert len(list(lines)) == 1
    assert (api.snapshots, api.clocked) == (1, ['resume', 'pause'])


def test_a_game_that_is_only_watched_keeps_its_clock() -> None:
    api = Scripted([update(4)])

    assert len(list(watch(api, 'alpha', 'en'))) == 1
    assert api.clocked == []
