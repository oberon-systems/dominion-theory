import pytest

from dominion_theory.engine import EVENTS, REASONS, Event, clock, events


def test_every_key_is_declared_once_with_its_values() -> None:
    declared = {getattr(module, name) for module in (clock, events) for name in dir(module) if name.endswith('ED')}

    assert declared == set(EVENTS)
    assert EVENTS['command-refused'] == ('id', 'reason')
    assert REASONS == ('refused-unknown-command', 'refused-unknown-seat')


def test_event_is_a_key_with_values() -> None:
    assert Event('command-accepted', {'id': 'c-1'}).data() == {'key': 'command-accepted', 'values': {'id': 'c-1'}}


@pytest.mark.parametrize(
    ('key', 'values'),
    [
        ('alpha-happened', {}),
        ('command-accepted', {}),
        ('command-accepted', {'id': 'c-1', 'reason': 'beta'}),
    ],
)
def test_undeclared_event_cannot_be_made(key: str, values: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=key):
        Event(key, values)
