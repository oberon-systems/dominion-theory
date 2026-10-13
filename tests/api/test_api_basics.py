from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX
from dominion_theory.api.schemas import STREAM, stream_schema
from dominion_theory.i18n import catalogue

# The table Addresses of docs/api/protocol.md, but for the stream, which OpenAPI does not describe.
ADDRESSES = {
    ('get', '/health'),
    ('get', '/profile'),
    ('patch', '/profile'),
    ('get', '/locales/{lang}'),
    ('get', '/presets'),
    ('post', '/games'),
    ('get', '/games'),
    ('get', '/games/{game_id}'),
    ('delete', '/games/{game_id}'),
    ('get', '/games/{game_id}/params'),
    ('get', '/games/{game_id}/snapshot'),
    ('get', '/games/{game_id}/biomes'),
    ('get', '/games/{game_id}/map'),
    ('post', '/games/{game_id}/commands'),
    ('post', '/games/{game_id}/clock'),
    ('get', '/games/{game_id}/record'),
}


def test_health_says_the_server_is_up(client: TestClient) -> None:
    answer = client.get(f'{PREFIX}/health')

    assert answer.status_code == 200
    assert answer.json() == {'status': 'ok'}


def test_the_local_profile_exists_from_the_start(client: TestClient) -> None:
    assert client.get(f'{PREFIX}/profile').json() == {'id': 'local', 'name': 'local', 'language': 'en'}


def test_the_language_and_the_name_of_the_profile_change(client: TestClient) -> None:
    changed = client.patch(f'{PREFIX}/profile', json={'language': 'ru'})
    renamed = client.patch(f'{PREFIX}/profile', json={'name': 'alpha'})

    assert changed.json() == {'id': 'local', 'name': 'local', 'language': 'ru'}
    assert renamed.json() == {'id': 'local', 'name': 'alpha', 'language': 'ru'}
    assert client.get(f'{PREFIX}/profile').json() == renamed.json()


def test_an_unknown_language_fails_the_check_of_a_profile(client: TestClient) -> None:
    answer = client.patch(f'{PREFIX}/profile', json={'language': 'xx'})

    assert answer.status_code == 422
    assert answer.json() == {'key': 'error-locale-unknown', 'values': {'locale': 'xx'}}


def test_a_body_with_an_unknown_name_cannot_be_read(client: TestClient) -> None:
    answer = client.patch(f'{PREFIX}/profile', json={'tongue': 'ru'})

    assert answer.status_code == 400
    assert answer.json() == {'key': 'error-request-unreadable', 'values': {}}


def test_a_catalogue_is_served_as_it_is(client: TestClient) -> None:
    answer = client.get(f'{PREFIX}/locales/ru')

    assert answer.status_code == 200
    assert answer.headers['content-type'].startswith('text/plain')
    assert answer.text == catalogue('ru')


def test_an_unknown_language_has_no_catalogue(client: TestClient) -> None:
    answer = client.get(f'{PREFIX}/locales/xx')

    assert answer.status_code == 404
    assert answer.json() == {'key': 'error-locale-unknown', 'values': {'locale': 'xx'}}


def test_the_presets_are_listed(client: TestClient) -> None:
    assert client.get(f'{PREFIX}/presets').json() == {'presets': ['harsh-winter']}


def test_the_openapi_document_holds_every_address(client: TestClient) -> None:
    paths = client.get(f'{PREFIX}/openapi.json').json()['paths']
    found = {(method, path.removeprefix(PREFIX)) for path, methods in paths.items() for method in methods}

    assert found >= ADDRESSES


def test_the_schema_of_the_stream_is_served_beside_it(client: TestClient) -> None:
    answer = client.get(f'{PREFIX}/updates.schema.json')

    assert answer.status_code == 200
    assert answer.json()['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert answer.json() == stream_schema()
    assert STREAM.json_schema().items() <= answer.json().items()
