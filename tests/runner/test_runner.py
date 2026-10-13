import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest

from dominion_theory.core.errors import DominionError
from dominion_theory.core.settings import Settings
from dominion_theory.engine import Command, Pass
from dominion_theory.runner import (
    CLOCK_RUNNING,
    GAME_ENDED,
    REAL_TIME,
    STEP,
    Ended,
    RealTimeRunner,
    Resync,
    Service,
    StepRunner,
    Update,
)
from dominion_theory.store import GameStore, ValkeyStore

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
DAY = 5
KEPT = 4
WAIT = 5


@pytest.fixture
def store() -> GameStore:
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    return ValkeyStore(raw, timedelta(hours=2))


@pytest.fixture
def service(store: GameStore, tmp_path: Path) -> Service:
    return Service(store, Settings(records_dir=tmp_path, tick_ms=2, updates_kept=KEPT))


async def updates(runner: RealTimeRunner, count: int) -> None:
    reached = asyncio.Event()
    target = runner.seq + count
    leave = runner.subscribe(lambda message: reached.set() if runner.seq >= target else None)
    await asyncio.wait_for(reached.wait(), WAIT)
    leave()


def test_the_mode_picks_the_runner(service: Service) -> None:
    assert isinstance(service.create(seed=1, overrides=SMALL, mode=STEP), StepRunner)
    assert isinstance(service.create(seed=1, overrides=SMALL), RealTimeRunner)


def test_a_step_game_waits_for_the_seat_and_advances_on_pass(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    seen: list[Update | Ended] = []
    runner.subscribe(seen.append)

    assert runner.snapshot()['waiting'] == ['player']
    assert runner.game.tick == 0

    runner.submit(Pass(seat='player', id='c-1'))

    assert runner.game.tick == 1
    assert [update.data() for update in seen if isinstance(update, Update)] == [
        {
            'seq': 1,
            'date': {'year': 1, 'month': 1, 'day': 1, 'part': 'midday', 'season': 'spring'},
            'events': [{'key': 'command-accepted', 'values': {'id': 'c-1'}}],
            'changes': {'units': [], 'gone': [], 'cells': [], 'seat': {}},
            'waiting': ['player'],
        }
    ]


def test_a_command_of_no_seat_does_not_answer_for_one(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)

    runner.submit(Command(seat='alpha', kind='pass'))

    assert runner.game.tick == 0
    assert runner.waiting == ['player']


def test_an_asked_step_advances_once(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)

    update = runner.step()

    assert runner.game.tick == 1
    assert update.seq == runner.seq == 1
    assert update.events == []


def test_a_repeated_command_is_taken_once(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)

    runner.submit(Pass(seat='player', id='c-1'))
    runner.submit(Pass(seat='player', id='c-1'))

    assert runner.game.tick == 1
    assert runner.waiting == ['player']


def test_the_snapshot_carries_the_last_update(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    for _ in range(3):
        runner.step()

    assert runner.snapshot() == {
        'seq': 3,
        'date': {'year': 1, 'month': 1, 'day': 1, 'part': 'evening', 'season': 'spring'},
        'window': {'scale': 0, 'x': 0, 'y': 0, 'width': 32, 'height': 16},
        'seat': {'name': 'player'},
        'units': [],
        'waiting': ['player'],
    }


def test_a_returning_subscriber_gets_what_it_missed_or_a_resync(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    for _ in range(KEPT + 2):
        runner.step()

    missed = runner.since(4)
    oldest = runner.since(2)

    assert isinstance(missed, list)
    assert isinstance(oldest, list)
    assert [update.seq for update in missed] == [5, 6]
    assert [update.seq for update in oldest] == [3, 4, 5, 6]
    assert runner.since(6) == []
    assert runner.since(1) == Resync(6)
    assert runner.since(9) == Resync(6)
    assert Resync(6).data() == {'resync': True, 'seq': 6}


def test_a_subscriber_that_left_hears_nothing(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    seen: list[Update | Ended] = []
    leave = runner.subscribe(seen.append)
    runner.step()

    leave()
    runner.step()

    assert len(seen) == 1


def test_the_store_holds_a_snapshot_of_the_day_and_the_ticks_since(service: Service, store: GameStore) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    for _ in range(DAY + 1):
        runner.step()
    runner.submit(Pass(seat='player', id='c-1'))

    held = store.load(runner.id)

    assert held is not None
    assert held.snapshot['tick'] == DAY
    assert held.snapshot['seq'] == DAY
    assert held.meta.tick == DAY + 2
    assert held.meta.mode == STEP
    assert held.meta.params == runner.game.params.hash
    assert held.changes == [
        {'changes': {'units': [], 'gone': [], 'cells': [], 'seat': {}}},
        {'seat': 'player', 'command': {'id': 'c-1', 'kind': 'pass'}},
        {'changes': {'units': [], 'gone': [], 'cells': [], 'seat': {}}},
    ]


def test_an_ended_game_leaves_the_store_and_takes_nothing(service: Service, store: GameStore) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    seen: list[Update | Ended] = []
    runner.subscribe(seen.append)
    runner.step()

    ended = runner.end('alpha')

    assert ended == Ended('alpha', 1, runner.game.state_hash())
    assert seen[-1] == ended
    assert store.live_games() == []
    assert store.load(runner.id) is None
    for refused in (runner.step, runner.end, lambda: runner.submit(Pass(seat='player'))):
        with pytest.raises(DominionError) as error:
            refused()
        assert error.value.message() == {'key': GAME_ENDED, 'values': {'id': runner.id}}


def test_a_step_game_has_no_clock(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)

    runner.resume()
    runner.set_speed(4)

    assert runner.running is False
    assert runner.game.tick == 0


def test_real_time_advances_stops_on_pause_and_resumes(service: Service) -> None:
    async def scenario() -> None:
        runner = service.create(seed=1, overrides=SMALL)
        assert isinstance(runner, RealTimeRunner)
        assert runner.running is False
        await asyncio.sleep(0.02)
        assert runner.game.tick == 0

        runner.resume()
        await updates(runner, 3)
        runner.pause()
        stopped = runner.game.tick

        assert stopped >= 3
        assert runner.running is False
        await asyncio.sleep(0.02)
        assert runner.game.tick == stopped

        runner.set_speed(2)
        runner.resume()
        await updates(runner, 2)
        runner.end()

        assert runner.game.tick >= stopped + 2
        assert runner.running is False
        assert runner.waiting == []

    asyncio.run(scenario())


def test_real_time_steps_by_hand_only_when_paused(service: Service) -> None:
    async def scenario() -> None:
        runner = service.create(seed=1, overrides=SMALL, mode=REAL_TIME)
        runner.submit(Pass(seat='player', id='c-1'))
        assert runner.game.tick == 0
        assert [event.data() for event in runner.step().events] == [
            {'key': 'command-accepted', 'values': {'id': 'c-1'}}
        ]

        runner.resume()
        with pytest.raises(DominionError) as error:
            runner.step()
        runner.pause()

        assert error.value.key == CLOCK_RUNNING

    asyncio.run(scenario())


def test_a_speed_is_above_zero(service: Service) -> None:
    runner = service.create(seed=1, overrides=SMALL)

    with pytest.raises(ValueError, match='above zero'):
        runner.set_speed(0)
