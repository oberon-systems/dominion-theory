import pytest
from pydantic import ValidationError

from dominion_theory.api.schemas import STREAM, ClockRequest, NewGame, Resync, Update, View, stream_schema
from dominion_theory.engine import Date, Event
from dominion_theory.runner import Resync as Behind
from dominion_theory.runner import Update as Handed


def test_what_a_runner_hands_out_fits_the_schema_of_the_stream() -> None:
    date = Date(1, 1, 2, 'morning', 'spring')
    events = [Event('command-accepted', {'id': 'c-1'})]
    handed = Handed(5, date, events, {'units': [], 'gone': [], 'cells': [], 'seat': {}}, ['player'])

    assert isinstance(STREAM.validate_python(handed.data()), Update)
    assert isinstance(STREAM.validate_python(Behind(5).data()), Resync)


def test_the_schema_describes_both_messages() -> None:
    schema = stream_schema()

    assert schema['$schema'].endswith('2020-12/schema')
    assert {'Update', 'Resync', 'Date', 'Message', 'Changes'} <= schema['$defs'].keys()
    assert set(schema['$defs']['Update']['required']) == {'seq', 'date', 'events', 'changes', 'waiting'}


def test_a_game_is_asked_for_with_nothing() -> None:
    asked = NewGame()

    assert (asked.seed, asked.preset, asked.overrides, asked.mode) == (None, None, None, 'real-time')


@pytest.mark.parametrize('body', [{'mode': 'alpha'}, {'seed': -1}, {'seed': 2**63}, {'alpha': 1}])
def test_a_game_asked_for_badly_is_not_read(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        NewGame.model_validate(body)


def test_speed_takes_a_value() -> None:
    assert ClockRequest(action='speed', value=2).value == 2
    assert ClockRequest(action='pause').value is None
    with pytest.raises(ValidationError):
        ClockRequest(action='speed')
    with pytest.raises(ValidationError):
        ClockRequest(action='speed', value=0)


def test_there_are_two_views() -> None:
    assert [view.value for view in View] == ['seat', 'spectator']
