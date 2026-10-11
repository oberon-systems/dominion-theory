import pytest

from dominion_theory.core.errors import DominionError


def test_error_carries_a_key_and_values() -> None:
    with pytest.raises(DominionError) as raised:
        raise DominionError('error-game-not-found', id='alpha')

    assert raised.value.key == 'error-game-not-found'
    assert raised.value.values == {'id': 'alpha'}
    assert raised.value.message() == {'key': 'error-game-not-found', 'values': {'id': 'alpha'}}


def test_error_without_values() -> None:
    assert DominionError('error-game-ended').message() == {'key': 'error-game-ended', 'values': {}}
