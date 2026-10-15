from collections.abc import Callable
from typing import Any

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX, create_app
from dominion_theory.api.schemas import STREAM, Update
from dominion_theory.core.settings import Settings
from dominion_theory.runner import Service

type NewGame = Callable[..., dict[str, Any]]

# A band that needs nothing, sees nothing and meets nothing: it camps, so the frame is tested alone.
QUIET = {
    'units.band.sight': 0,
    'units.band.consumption_per_day.forage': 0.0,
    'units.band.consumption_per_day.water': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
    'units.band.people.injury.per_day': 0.0,
    'units.band.people.age.per_year': 0.0,
    'units.band.people.stages.adult.dies.frailty': 0.0,
    'encounters.chance': 0.0,
}
SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16, **QUIET}
STEP = {'action': 'step'}


def step(client: TestClient, game: str, times: int = 1) -> None:
    for _ in range(times):
        assert client.post(f'{PREFIX}/games/{game}/clock', json=STEP).status_code == 200


def test_the_stream_joins_right_after_the_snapshot(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']
    step(client, game, 2)
    seq = client.get(f'{PREFIX}/games/{game}/snapshot').json()['seq']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after={seq}') as stream:
        step(client, game, 3)
        updates = [stream.receive_json() for _ in range(3)]

    assert seq == 2
    assert [update['seq'] for update in updates] == [3, 4, 5]
    assert all(isinstance(STREAM.validate_python(update), Update) for update in updates)
    assert updates[2]['events'] == [{'key': 'day-started', 'values': {'year': 1, 'month': 1, 'day': 2}}]
    assert {**updates[2]['changes'], 'units': []} == {'units': [], 'gone': [], 'cells': [], 'known': [], 'seat': {}}


def test_a_client_that_returns_in_time_is_sent_what_it_missed(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']
    step(client, game, 5)

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=2') as stream:
        missed = [stream.receive_json()['seq'] for _ in range(3)]
        step(client, game)
        following = stream.receive_json()['seq']

    assert missed == [3, 4, 5]
    assert following == 6


def test_a_stream_opened_with_an_old_seq_gets_resync(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']
    step(client, game, 7)

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=1') as stream:
        first = stream.receive_json()
        step(client, game)
        following = stream.receive_json()

    assert first == {'resync': True, 'seq': 7}
    assert following['seq'] == 8


def test_a_stream_without_after_starts_at_the_present(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']
    step(client, game, 2)

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates') as stream:
        step(client, game)
        following = stream.receive_json()

    assert following['seq'] == 3


def test_the_stream_of_an_unknown_game_closes_with_a_message(client: TestClient) -> None:
    with client.websocket_connect(f'{PREFIX}/games/alpha/updates') as stream:
        message = stream.receive_json()
        with pytest.raises(WebSocketDisconnect) as closed:
            stream.receive_json()

    assert message == {'key': 'error-game-not-found', 'values': {'id': 'alpha'}}
    assert closed.value.code == 4404


def test_the_stream_closes_when_the_game_ends(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?after=0') as stream:
        client.delete(f'{PREFIX}/games/{game}')
        with pytest.raises(WebSocketDisconnect) as closed:
            stream.receive_json()

    assert closed.value.code == 1000
    with client.websocket_connect(f'{PREFIX}/games/{game}/updates') as stream:
        assert stream.receive_json() == {'key': 'error-game-ended', 'values': {'id': game}}


def test_the_spectator_stream_is_a_setting(settings: Settings, service: Service) -> None:
    closed = settings.model_copy(update={'spectator': False})

    with TestClient(create_app(closed, service)) as client:
        game = client.post(f'{PREFIX}/games', json={'overrides': SMALL, 'mode': 'step'}).json()['id']
        with client.websocket_connect(f'{PREFIX}/games/{game}/updates?view=spectator') as stream:
            message = stream.receive_json()
            with pytest.raises(WebSocketDisconnect) as refused:
                stream.receive_json()
        with client.websocket_connect(f'{PREFIX}/games/{game}/updates?view=seat&after=0') as stream:
            step(client, game)
            update = stream.receive_json()

    assert message == {'key': 'error-request-unreadable', 'values': {}}
    assert refused.value.code == 4400
    assert update['seq'] == 1


def test_the_spectator_stream_is_offered_by_default(client: TestClient, new_game: NewGame) -> None:
    game = new_game()['id']

    with client.websocket_connect(f'{PREFIX}/games/{game}/updates?view=spectator&after=0') as stream:
        step(client, game)
        update = stream.receive_json()

    assert update['seq'] == 1
