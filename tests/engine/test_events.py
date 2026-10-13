import pytest

from dominion_theory.engine import EVENTS, REASONS, Event, clock, events


def test_every_key_is_declared_once_with_its_values() -> None:
    held = {name: value for module in (clock, events) for name, value in vars(module).items() if name.isupper()}
    prefixes = ('STATE', 'KIND', 'PROPOSAL')
    declared = {key for name, key in held.items() if isinstance(key, str) and name not in prefixes} - set(REASONS)

    assert declared == set(EVENTS)
    assert EVENTS['command-refused'] == ('id', 'reason')
    assert REASONS == (
        'refused-unknown-command',
        'refused-unknown-seat',
        'refused-council-too-soon',
        'refused-proposal-pending',
        'refused-no-such-direction',
        'refused-seat-banished',
    )


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
