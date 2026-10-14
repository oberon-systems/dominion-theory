import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.api.index import Index
from dominion_theory.core.errors import DominionError
from dominion_theory.core.settings import Settings
from dominion_theory.db import Database, local_profile
from dominion_theory.runner import Service, record_path

type NewGame = Callable[..., dict[str, Any]]

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
DYING = {**SMALL, 'units.band.consumption_per_day.water': 100.0, 'units.band.states.thirst.loss_per_day': 0.9}
DOOMED = {**SMALL, 'council.status.start': 1}
STEP = ('clock', {'action': 'step'})
SILENT = ('commands', {'id': 'c-1', 'kind': 'vote', 'proposal': {'kind': 'abstain'}})


@pytest.fixture
def index(tmp_path: Path) -> Index:
    database = Database(f'sqlite:///{tmp_path}/alpha.db')
    database.upgrade()
    with database.session() as session:
        local_profile(session)
    return Index(database)


def test_the_row_follows_the_life_of_the_game(client: TestClient, new_game: NewGame) -> None:
    before = int(time.time())
    created = new_game(seed=42, preset='harsh-winter')
    started = client.get(f'{PREFIX}/games').json()['games']
    for _ in range(3):
        client.post(f'{PREFIX}/games/{created["id"]}/clock', json={'action': 'step'})
    running = client.get(f'{PREFIX}/games').json()['games']

    ended = client.delete(f'{PREFIX}/games/{created["id"]}')
    finished = client.get(f'{PREFIX}/games').json()['games']

    assert (
        started
        == running
        == [
            {
                'id': created['id'],
                'seed': 42,
                'params_hash': created['params_hash'],
                'preset': 'harsh-winter',
                'started_at': started[0]['started_at'],
                'finished_at': None,
                'outcome': None,
                'last_tick': 0,
            }
        ]
    )
    assert started[0]['started_at'] >= before
    assert ended.status_code == 200
    assert finished == [ended.json()]
    assert (finished[0]['outcome'], finished[0]['last_tick']) == ('stopped', 3)
    assert finished[0]['finished_at'] >= started[0]['started_at']


@pytest.mark.parametrize(
    ('overrides', 'asked', 'outcome', 'event'),
    [(DYING, [STEP] * 5, 'died', 'band-died'), (DOOMED, [SILENT], 'banished', 'seat-banished')],
)
def test_a_game_the_rules_end_reaches_the_index(
    client: TestClient,
    new_game: NewGame,
    overrides: dict[str, Any],
    asked: list[tuple[str, dict[str, Any]]],
    outcome: str,
    event: str,
) -> None:
    before = int(time.time())
    game = new_game(seed=42, overrides=overrides, seated=True)['id']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=0') as stream:
        for address, body in asked:
            assert client.post(f'{PREFIX}/games/{game}/{address}', json=body).status_code == 200
        updates = [stream.receive_json() for _ in asked]
    (row,) = client.get(f'{PREFIX}/games').json()['games']
    later = client.post(f'{PREFIX}/games/{game}/commands', json={'id': 'c-9', 'kind': 'pass'})

    assert event in [held['key'] for held in updates[-1]['events']]
    assert updates[-1]['waiting'] == []
    assert (row['outcome'], row['last_tick']) == (outcome, len(asked))
    assert isinstance(row['finished_at'], int) and row['finished_at'] >= before
    assert later.status_code == 409
    assert later.json() == {'key': 'error-game-ended', 'values': {'id': game}}


def test_the_index_lists_every_game_in_the_order_they_started(client: TestClient, new_game: NewGame) -> None:
    first, second = new_game(), new_game()
    client.delete(f'{PREFIX}/games/{first["id"]}')

    games = client.get(f'{PREFIX}/games').json()['games']

    assert {game['id'] for game in games} == {first['id'], second['id']}
    assert [game['started_at'] for game in games] == sorted(game['started_at'] for game in games)
    assert {game['id']: game['outcome'] for game in games} == {first['id']: 'stopped', second['id']: None}


def test_the_row_points_at_the_record(index: Index, service: Service, settings: Settings) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode='step')

    row = index.add(runner)

    assert index.find(runner.id).record_path == str(record_path(settings.records_dir, runner.id))
    assert (row.profile_id, row.seed, row.params_hash, row.preset) == ('local', 7, runner.game.params.hash, None)
    assert [found.id for found in index.rows()] == [runner.id]


def test_a_followed_game_is_marked_when_it_ends(index: Index, service: Service) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode='step')
    index.add(runner)
    runner.step()
    runner.step()

    service.end(runner.id, 'banished')
    row = index.find(runner.id)

    assert (row.last_tick, row.outcome) == (2, 'banished')
    assert row.finished_at is not None


def test_a_game_the_index_does_not_hold_is_not_found(index: Index, service: Service) -> None:
    runner = service.create(seed=7, overrides=SMALL, mode='step')
    index.follow(runner)

    service.end(runner.id)

    with pytest.raises(DominionError) as raised:
        index.find(runner.id)
    assert raised.value.message() == {'key': 'error-game-not-found', 'values': {'id': runner.id}}
    assert index.rows() == []
