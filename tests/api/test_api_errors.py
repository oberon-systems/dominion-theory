import pytest
from fluent.syntax import FluentParser, ast

from dominion_theory.api.errors import STATUSES, ApiError, body_of, status_of
from dominion_theory.core.errors import DominionError
from dominion_theory.i18n import LANGUAGES, catalogue

# The table Errors of docs/api/protocol.md.
TABLE = {400, 404, 409, 422}


@pytest.mark.parametrize('lang', LANGUAGES)
def test_every_error_key_the_api_can_return_exists_in_the_catalogue(lang: str) -> None:
    entries = FluentParser().parse(catalogue(lang)).body
    keys = {entry.id.name for entry in entries if isinstance(entry, ast.Message)}

    assert STATUSES.keys() - keys == set()


def test_every_status_is_one_of_the_table() -> None:
    assert set(STATUSES.values()) == TABLE


@pytest.mark.parametrize(
    ('key', 'status'),
    [
        ('error-request-unreadable', 400),
        ('error-game-not-found', 404),
        ('error-preset-not-found', 404),
        ('error-locale-unknown', 404),
        ('error-game-ended', 409),
        ('error-params-invalid', 422),
        ('error-command-invalid', 422),
    ],
)
def test_a_key_has_its_status(key: str, status: int) -> None:
    assert status_of(DominionError(key)) == status


def test_an_error_may_carry_a_status_of_its_own() -> None:
    error = ApiError(422, 'error-locale-unknown', locale='xx')

    assert status_of(error) == 422
    assert body_of(error) == {'key': 'error-locale-unknown', 'values': {'locale': 'xx'}}


def test_a_key_the_api_does_not_know_is_a_fault_of_the_server() -> None:
    assert status_of(DominionError('alpha')) == 500


def test_the_body_is_a_message_that_can_be_written_as_json() -> None:
    error = DominionError('error-params-invalid', path='alpha.beta', found=(1, 2), expected='a number')

    assert body_of(error) == {
        'key': 'error-params-invalid',
        'values': {'path': 'alpha.beta', 'found': [1, 2], 'expected': 'a number'},
    }
