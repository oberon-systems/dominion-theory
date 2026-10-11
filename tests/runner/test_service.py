import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest

from dominion_theory.core.errors import DominionError
from dominion_theory.core.settings import Settings
from dominion_theory.engine import Pass
from dominion_theory.runner import GAME_NOT_FOUND, REAL_TIME, STEP, RealTimeRunner, Service, read, replay
from dominion_theory.store import GameStore, ValkeyStore

SMALL = {'planet.window.width': 32, 'planet.window.height': 16}
DAY = 5


@pytest.fixture
def store() -> GameStore:
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    return ValkeyStore(raw, timedelta(hours=2))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(records_dir=tmp_path, tick_ms=2)


@pytest.fixture
def service(store: GameStore, settings: Settings) -> Service:
    return Service(store, settings)


def test_how_many_updates_are_kept_is_a_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings().updates_kept == 512

    monkeypatch.setenv('DT_UPDATES_KEPT', '8')

    assert Settings().updates_kept == 8


def test_a_created_game_is_found_listed_and_stored(service: Service, store: GameStore) -> None:
    runner = service.create(seed=42, preset='harsh-winter', overrides=SMALL, mode=STEP)

    assert service.find(runner.id) is runner
    assert service.games() == [runner]
    assert store.live_games() == [runner.id]
    assert runner.game.seed == 42
    assert runner.game.tick == 0
    assert [season.name for season in runner.game.params.time.seasons] == ['spring', 'summer', 'autumn', 'winter']
    assert runner.game.params.time.seasons[3].months == 4


def test_a_seed_left_out_is_drawn(service: Service) -> None:
    first = service.create(overrides=SMALL, mode=STEP)
    second = service.create(overrides=SMALL, mode=STEP)

    assert first.game.seed != second.game.seed
    assert first.id != second.id


def test_parameters_that_fail_their_check_make_no_game(service: Service, store: GameStore, tmp_path: Path) -> None:
    with pytest.raises(DominionError) as error:
        service.create(overrides={'planet.window.width': 1})

    assert error.value.values['path'] == 'planet.window.width'
    assert service.games() == []
    assert store.live_games() == []
    assert list(tmp_path.iterdir()) == []


def test_an_unknown_game_is_not_found(service: Service) -> None:
    for refused in (service.find, service.end):
        with pytest.raises(DominionError) as error:
            refused('alpha')

        assert error.value.message() == {'key': GAME_NOT_FOUND, 'values': {'id': 'alpha'}}


def test_an_ended_game_is_forgotten_and_its_record_closed(service: Service, store: GameStore) -> None:
    runner = service.create(seed=1, overrides=SMALL, mode=STEP)
    runner.step()

    ended = service.end(runner.id, 'alpha')

    assert ended.outcome == 'alpha'
    assert ended.tick == 1
    assert service.games() == []
    assert store.live_games() == []
    assert read(runner.record_path)[-1]['t'] == 'footer'
    with pytest.raises(DominionError):
        service.find(runner.id)


@pytest.mark.parametrize('mode', [STEP, REAL_TIME])
def test_after_a_restart_a_game_comes_back_paused_at_its_tick(store: GameStore, settings: Settings, mode: str) -> None:
    before = Service(store, settings).create(seed=7, overrides=SMALL, mode=mode)
    before.submit(Pass(seat='player', id='c-1'))
    for _ in range(DAY + 2):
        before.step()
    before.submit(Pass(seat='player', id='c-2'))
    if mode == REAL_TIME:
        before.step()

    after = Service(store, settings)
    (runner,) = after.restore()

    assert after.find(before.id) is runner
    assert runner is not before
    assert runner.mode == mode
    assert runner.running is False
    assert runner.game.tick == before.game.tick
    assert runner.seq == before.seq
    assert runner.game.state_hash() == before.game.state_hash()
    assert runner.snapshot() == before.snapshot()
    assert after.restore() == []


def test_a_restored_game_goes_on_and_its_record_replays(store: GameStore, settings: Settings) -> None:
    before = Service(store, settings).create(seed=7, overrides=SMALL, mode=STEP)
    for _ in range(DAY + 2):
        before.submit(Pass(seat='player'))

    after = Service(store, settings)
    (runner,) = after.restore()
    runner.submit(Pass(seat='player', id='player-1'))
    for _ in range(DAY):
        runner.submit(Pass(seat='player'))
    after.end(runner.id)

    result = replay(runner.record_path)
    ticks = [line['tick'] for line in read(runner.record_path) if line['t'] == 'tick']

    assert runner.game.tick == 2 * DAY + 2
    assert ticks == list(range(1, 2 * DAY + 3))
    assert result.matched is True
    assert result.game.state_hash() == runner.game.state_hash()


def test_a_command_not_yet_judged_comes_back_with_its_game(store: GameStore, settings: Settings) -> None:
    before = Service(store, settings).create(seed=7, overrides=SMALL, mode=REAL_TIME)
    for _ in range(DAY - 1):
        before.step()
    before.submit(Pass(seat='player', id='c-1'))
    before.step()
    before.submit(Pass(seat='player', id='c-2'))
    before.step()
    before.submit(Pass(seat='player', id='c-3'))

    (runner,) = Service(store, settings).restore()
    runner.submit(Pass(seat='player', id='c-2'))
    update = runner.step()

    assert runner.game.tick == DAY + 2
    assert [event.data() for event in update.events] == [{'key': 'command-accepted', 'values': {'id': 'c-3'}}]
    assert [line['command']['id'] for line in read(runner.record_path) if line['t'] == 'command'] == ['c-1']


def test_a_restored_clock_starts_when_asked(store: GameStore, settings: Settings) -> None:
    async def scenario() -> None:
        Service(store, settings).create(seed=7, overrides=SMALL)
        (runner,) = Service(store, settings).restore()
        assert isinstance(runner, RealTimeRunner)
        ticked = asyncio.Event()
        runner.subscribe(lambda message: ticked.set())

        runner.resume()
        await asyncio.wait_for(ticked.wait(), 5)
        runner.pause()

        assert runner.game.tick >= 1

    asyncio.run(scenario())


def test_a_game_with_no_copy_is_not_restored(store: GameStore, settings: Settings) -> None:
    runner = Service(store, settings).create(seed=7, overrides=SMALL, mode=STEP)
    runner.end()

    assert Service(store, settings).restore() == []
