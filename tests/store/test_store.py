from datetime import timedelta
from typing import Any

import fakeredis
import numpy as np
import pytest

from dominion_theory.content import load_params
from dominion_theory.core.settings import Settings
from dominion_theory.engine.game import Game
from dominion_theory.store import GameStore, Meta, ValkeyStore, open_store

TTL = timedelta(hours=2)
META = Meta(seed=42, params='alpha', tick=0, mode='step')
GAME_KEYS = {b'dt:game:alpha:meta', b'dt:game:alpha:snapshot', b'dt:game:alpha:changes'}


def snapshot(tick: int = 0) -> dict[str, Any]:
    return {'tick': tick, 'era': 'band', 'grids': {'biomes': np.arange(6, dtype=np.uint8).reshape(2, 3)}}


@pytest.fixture
def raw() -> Any:
    return fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))


@pytest.fixture
def store(raw: Any) -> GameStore:
    return ValkeyStore(raw, TTL)


def test_a_saved_snapshot_loads_back_equal(store: GameStore) -> None:
    store.save_snapshot('alpha', snapshot(), META)

    held = store.load('alpha')

    assert held is not None
    assert held.meta == META
    assert held.changes == []
    assert held.snapshot['tick'] == 0
    assert held.snapshot['era'] == 'band'
    assert held.snapshot['grids']['biomes'].dtype == np.uint8
    assert np.array_equal(held.snapshot['grids']['biomes'], snapshot()['grids']['biomes'])


def test_a_game_never_saved_loads_as_nothing(store: GameStore) -> None:
    assert store.load('alpha') is None


def test_changes_come_back_in_order(store: GameStore) -> None:
    store.save_snapshot('alpha', snapshot(), META)
    for tick in (1, 2, 3):
        store.append_changes('alpha', tick, {'units': [tick], 'seat': {}})

    held = store.load('alpha')

    assert held is not None
    assert held.changes == [{'units': [tick], 'seat': {}} for tick in (1, 2, 3)]
    assert held.meta.tick == 3
    assert held.snapshot['tick'] == 0


def test_the_next_snapshot_forgets_the_changes(store: GameStore) -> None:
    store.save_snapshot('alpha', snapshot(), META)
    store.append_changes('alpha', 1, {'units': [1]})
    store.save_snapshot('alpha', snapshot(2), Meta(seed=42, params='alpha', tick=2, mode='step'))

    held = store.load('alpha')

    assert held is not None
    assert held.changes == []
    assert held.snapshot['tick'] == 2
    assert held.meta.tick == 2


def test_live_games_lists_what_was_saved_and_not_what_was_dropped(store: GameStore) -> None:
    store.save_snapshot('beta', snapshot(), META)
    store.save_snapshot('alpha', snapshot(), META)
    assert store.live_games() == ['alpha', 'beta']

    store.drop('beta')

    assert store.live_games() == ['alpha']


def test_drop_removes_every_key_of_the_game_and_nothing_of_another(store: GameStore, raw: Any) -> None:
    for game_id in ('alpha', 'beta'):
        store.save_snapshot(game_id, snapshot(), META)
        store.append_changes(game_id, 1, {'units': []})

    store.drop('beta')

    assert set(raw.keys('*')) == GAME_KEYS | {b'dt:games'}
    assert set(raw.smembers('dt:games')) == {b'alpha'}
    assert store.load('beta') is None
    assert store.load('alpha') is not None


def test_every_key_is_under_the_prefix(store: GameStore, raw: Any) -> None:
    store.save_snapshot('alpha', snapshot(), META)
    store.append_changes('alpha', 1, {'units': []})

    assert set(raw.keys('*')) == GAME_KEYS | {b'dt:games'}
    assert raw.type('dt:games') == b'set'
    assert raw.type('dt:game:alpha:meta') == b'hash'
    assert raw.type('dt:game:alpha:snapshot') == b'string'
    assert raw.type('dt:game:alpha:changes') == b'list'


def test_keys_of_a_game_carry_the_expiry(store: GameStore, raw: Any) -> None:
    store.save_snapshot('alpha', snapshot(), META)
    store.append_changes('alpha', 1, {'units': []})

    for name in GAME_KEYS:
        assert 0 < raw.ttl(name) <= TTL.total_seconds()


def test_a_write_renews_the_expiry(store: GameStore, raw: Any) -> None:
    store.save_snapshot('alpha', snapshot(), META)
    store.append_changes('alpha', 1, {'units': []})
    for name in GAME_KEYS:
        raw.expire(name, 10)

    store.append_changes('alpha', 2, {'units': []})

    for name in GAME_KEYS:
        assert raw.ttl(name) > 10


def test_an_expired_game_is_not_live(store: GameStore, raw: Any) -> None:
    store.save_snapshot('alpha', snapshot(), META)
    store.save_snapshot('beta', snapshot(), META)
    raw.delete(*(name.replace(b'alpha', b'beta') for name in GAME_KEYS))

    assert store.live_games() == ['alpha']
    assert set(raw.smembers('dt:games')) == {b'alpha'}


def test_two_stores_of_the_same_settings_see_the_same_data() -> None:
    settings = Settings(store_url='', store_ttl=TTL)
    first, second = open_store(settings), open_store(settings)

    first.save_snapshot('alpha', snapshot(), META)
    try:
        held = second.load('alpha')
        assert held is not None
        assert held.meta == META
        assert second.live_games() == ['alpha']
    finally:
        first.drop('alpha')

    assert second.live_games() == []


def test_a_game_of_the_engine_is_restored_from_the_store(store: GameStore) -> None:
    small = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
    game = Game.create(seed=42, params=load_params(overrides=small))
    game.step()
    store.save_snapshot('alpha', game.snapshot(), Meta(game.seed, game.params.hash, game.tick, 'step'))

    held = store.load('alpha')

    assert held is not None
    assert Game.restore(held.snapshot).state_hash() == game.state_hash()
