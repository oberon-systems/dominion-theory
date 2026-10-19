from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX, create_app
from dominion_theory.core.settings import Settings
from dominion_theory.runner import Service

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
START = {'year': 1, 'month': 1, 'day': 1, 'part': 'morning', 'season': 'spring'}

type NewGame = Callable[..., dict[str, Any]]


def test_a_game_is_created_with_a_preset_and_overrides(client: TestClient, new_game: NewGame) -> None:
    created = new_game(seed=42, preset='harsh-winter')
    params = client.get(f'{PREFIX}/games/{created["id"]}/params').json()

    assert created == {
        'id': created['id'],
        'seed': 42,
        'params_hash': created['params_hash'],
        'mode': 'step',
        'running': False,
        'date': START,
    }
    assert len(created['params_hash']) == 64
    assert (params['planet']['window']['width'], params['planet']['window']['height']) == (32, 16)
    assert params['time']['seasons'][3] == {'name': 'winter', 'months': 4}
    assert client.get(f'{PREFIX}/games/{created["id"]}').json() == created


def test_what_is_left_out_is_drawn_or_default(client: TestClient) -> None:
    first = client.post(f'{PREFIX}/games', json={'overrides': SMALL}).json()
    second = client.post(f'{PREFIX}/games', json={'overrides': SMALL}).json()

    assert first['mode'] == 'real-time'
    assert first['running'] is False
    assert first['date'] == START
    assert first['seed'] != second['seed']


@pytest.mark.parametrize(
    ('overrides', 'path', 'found'),
    [
        ({'planet.window.width': 2}, 'planet.window.width', 2),
        ({'peoples.bands': 8}, 'peoples.bands', 'peoples'),
    ],
)
def test_a_bad_override_is_refused_with_its_path(
    client: TestClient, overrides: dict[str, Any], path: str, found: object
) -> None:
    answer = client.post(f'{PREFIX}/games', json={'overrides': overrides})
    values = answer.json()['values']

    assert answer.status_code == 422
    assert answer.json()['key'] == 'error-params-invalid'
    assert (values['path'], values['found']) == (path, found)
    assert values['expected']
    assert client.get(f'{PREFIX}/games').json() == {'games': []}


def test_an_unknown_preset_is_not_found(client: TestClient) -> None:
    answer = client.post(f'{PREFIX}/games', json={'preset': 'alpha'})

    assert answer.status_code == 404
    assert answer.json() == {'key': 'error-preset-not-found', 'values': {'id': 'alpha'}}


@pytest.mark.parametrize('body', [{'mode': 'alpha'}, {'seed': -1}, {'speed': 2}, [1]])
def test_a_request_that_cannot_be_read_is_400(client: TestClient, body: object) -> None:
    answer = client.post(f'{PREFIX}/games', json=body)

    assert answer.status_code == 400
    assert answer.json() == {'key': 'error-request-unreadable', 'values': {}}


REQUESTS: list[tuple[str, str, dict[str, Any] | None]] = [
    ('GET', '', None),
    ('DELETE', '', None),
    ('GET', '/params', None),
    ('GET', '/snapshot', None),
    ('GET', '/biomes', None),
    ('GET', '/map', None),
    ('POST', '/commands', {'id': 'c-1', 'kind': 'pass'}),
    ('POST', '/clock', {'action': 'step'}),
]


@pytest.mark.parametrize(('method', 'address', 'body'), [*REQUESTS, ('GET', '/record', None)])
def test_an_unknown_game_is_404_with_a_message_key(
    client: TestClient, method: str, address: str, body: dict[str, Any] | None
) -> None:
    answer = client.request(method, f'{PREFIX}/games/alpha{address}', json=body)

    assert answer.status_code == 404
    assert answer.json() == {'key': 'error-game-not-found', 'values': {'id': 'alpha'}}


@pytest.mark.parametrize(('method', 'address', 'body'), REQUESTS)
def test_an_ended_game_is_409(
    client: TestClient, new_game: NewGame, method: str, address: str, body: dict[str, Any] | None
) -> None:
    game = new_game()['id']
    client.delete(f'{PREFIX}/games/{game}')

    answer = client.request(method, f'{PREFIX}/games/{game}{address}', json=body)

    assert answer.status_code == 409
    assert answer.json() == {'key': 'error-game-ended', 'values': {'id': game}}


def test_the_snapshot_is_what_the_caller_may_see(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']

    seat = client.get(f'{PREFIX}/games/{game}/snapshot')
    spectator = client.get(f'{PREFIX}/games/{game}/snapshot', params={'view': 'spectator'})

    shown = seat.json()
    window = shown.pop('window')
    (band,) = shown.pop('units')
    place = band.pop('place')

    assert shown == {
        'seq': 0,
        'date': START,
        'seat': {'name': 'player', 'unit': 1, 'status': 50.0, 'seated': False, 'council': None},
        'waiting': ['player'],
    }
    assert band == {
        'id': 1,
        'kind': 'band',
        'population': 15,
        'ages': {'child': 0, 'adult': 15, 'elder': 0},
        'pregnant': 0,
        'injured': 0,
        'wounds': {'light': 0, 'medium': 0, 'heavy': 0},
        'sick': 0,
        'stores': {'forage': 15.0, 'water': 15.0},
        'goods': {},
        'kit': {'litters': 0, 'spears': 0, 'clothes': 0},
        'fatigue': 0.0,
        'states': [],
        'action': {'kind': 'camp'},
        'intent': None,
        'route': [],
        'roles': {'gatherer': 15, 'nanny': 0, 'hunter': 0},
        'camp': None,
        'reason': None,
        'lore': [],
    }
    assert place['scale'] == 0
    assert window['x'] <= place['x'] < window['x'] + 32
    assert window['y'] <= place['y'] < window['y'] + 16
    assert (window['scale'], window['width'], window['height']) == (0, 32, 16)
    assert 0 <= window['x'] <= 400 - 32
    assert 0 <= window['y'] <= 200 - 16
    assert spectator.json() == seat.json()
    assert client.get(f'{PREFIX}/games/{game}/snapshot', params={'view': 'alpha'}).status_code == 400


def test_the_spectator_view_is_a_setting(settings: Settings, service: Service) -> None:
    closed = settings.model_copy(update={'spectator': False})
    with TestClient(create_app(closed, service)) as client:
        game = client.post(f'{PREFIX}/games', json={'overrides': SMALL, 'mode': 'step'}).json()['id']

        refused = [
            client.get(f'{PREFIX}/games/{game}/{address}', params={'view': 'spectator'})
            for address in ('snapshot', 'map', 'biomes')
        ]
        seat = client.get(f'{PREFIX}/games/{game}/snapshot', params={'view': 'seat'})

    assert [answer.status_code for answer in refused] == [400, 400, 400]
    assert refused[0].json() == {'key': 'error-request-unreadable', 'values': {}}
    assert seat.status_code == 200
