from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX, create_app
from dominion_theory.core.settings import Settings
from dominion_theory.db import LOCAL_PROFILE, Database, find_profile
from dominion_theory.runner import Service
from dominion_theory.store import GameStore

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}


def test_the_factory_serves_under_the_versioned_address(client: TestClient) -> None:
    assert PREFIX == '/api/v1'
    assert client.get('/health').status_code == 404
    assert client.get(f'{PREFIX}/docs').status_code == 200


def test_starting_makes_the_tables_and_the_local_profile(settings: Settings, service: Service) -> None:
    with TestClient(create_app(settings, service)), Database(settings.database_url).session() as session:
        profile = find_profile(session, LOCAL_PROFILE)

    assert (profile.id, profile.locale) == ('local', 'en')


def test_a_server_that_starts_again_restores_its_live_games(settings: Settings, store: GameStore) -> None:
    with TestClient(create_app(settings, Service(store, settings))) as first:
        game = first.post(f'{PREFIX}/games', json={'seed': 42, 'overrides': SMALL, 'mode': 'step'}).json()
        ended = first.post(f'{PREFIX}/games', json={'overrides': SMALL, 'mode': 'step'}).json()
        first.delete(f'{PREFIX}/games/{ended["id"]}')
        for _ in range(2):
            first.post(f'{PREFIX}/games/{game["id"]}/clock', json={'action': 'step'})

    with TestClient(create_app(settings, Service(store, settings))) as second:
        restored = second.get(f'{PREFIX}/games/{game["id"]}')
        snapshot = second.get(f'{PREFIX}/games/{game["id"]}/snapshot').json()
        gone = second.get(f'{PREFIX}/games/{ended["id"]}')
        second.delete(f'{PREFIX}/games/{game["id"]}')
        rows = second.get(f'{PREFIX}/games').json()['games']

    assert restored.status_code == 200
    assert restored.json() == {**game, 'date': snapshot['date']}
    assert (snapshot['seq'], snapshot['date']['part']) == (2, 'afternoon')
    assert gone.status_code == 409
    assert {row['id']: (row['outcome'], row['last_tick']) for row in rows} == {
        game['id']: ('stopped', 2),
        ended['id']: ('stopped', 0),
    }


def test_stopping_the_server_stops_the_clocks(settings: Settings, service: Service) -> None:
    with TestClient(create_app(settings, service)) as client:
        game = client.post(f'{PREFIX}/games', json={'overrides': SMALL}).json()['id']
        running = client.post(f'{PREFIX}/games/{game}/clock', json={'action': 'resume'}).json()['running']

    assert running is True
    assert service.find(game).running is False
