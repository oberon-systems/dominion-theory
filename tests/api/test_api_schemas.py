import pytest
from pydantic import ValidationError

from dominion_theory.api.schemas import (
    STREAM,
    ClockRequest,
    Intent,
    NewGame,
    Resync,
    SeatChange,
    Snapshot,
    StayProposal,
    Update,
    View,
    stream_schema,
)
from dominion_theory.engine import CallCouncil, Date, Event, Pass
from dominion_theory.runner import Resync as Behind
from dominion_theory.runner import Service
from dominion_theory.runner import Update as Handed

PLANET = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
STAY = {'kind': 'stay-and-gather'}


def test_what_a_runner_hands_out_fits_the_schema_of_the_stream() -> None:
    date = Date(1, 1, 2, 'morning', 'spring')
    events = [Event('command-accepted', {'id': 'c-1'})]
    handed = Handed(5, date, events, {'units': [], 'gone': [], 'cells': [], 'known': [], 'seat': {}}, ['player'])

    assert isinstance(STREAM.validate_python(handed.data()), Update)
    assert isinstance(STREAM.validate_python(Behind(5).data()), Resync)


def test_the_band_and_its_council_fit_the_snapshot_and_the_stream_and_lose_nothing(service: Service) -> None:
    runner = service.create(seed=42, overrides=PLANET, mode='step')
    sent: list[Handed] = []
    runner.subscribe(lambda message: sent.append(message) if isinstance(message, Handed) else None)
    runner.submit(CallCouncil(seat='player', proposal=STAY, id='c-1'))
    for tick in range(1, 12):
        runner.submit(Pass(seat='player', id=f'p-{tick}'))

    read = [STREAM.validate_python(update.data()) for update in sent]
    snapshot = Snapshot.model_validate(runner.snapshot())

    assert all(isinstance(update, Update) for update in read)
    assert [update.model_dump(exclude_unset=True) for update in read] == [update.data() for update in sent]
    assert snapshot.model_dump(exclude_unset=True) == runner.snapshot()
    first, verdict = read[0], read[9]
    assert isinstance(first, Update) and isinstance(verdict, Update)
    assert first.changes.units[0].intent == Intent(proposal=StayProposal(kind='stay-and-gather'), until=10)
    assert first.changes.seat == SeatChange(council_from=10)
    assert verdict.changes.seat == SeatChange(status=53.0)
    assert snapshot.seat.status == 53.0


def test_the_schema_describes_both_messages() -> None:
    schema = stream_schema()

    assert schema['$schema'].endswith('2020-12/schema')
    assert {'Update', 'Resync', 'Date', 'Message', 'Changes', 'Cell', 'Known', 'Unit', 'SeatChange'} <= schema[
        '$defs'
    ].keys()
    assert set(schema['$defs']['Known']['required']) == {'x', 'y', 'biome', 'river', 'seen'}
    assert set(schema['$defs']['Cell']['required']) == {'x', 'y'}
    assert set(schema['$defs']['Update']['required']) == {'seq', 'date', 'events', 'changes', 'waiting'}


def test_a_changed_cell_is_its_place_and_a_stock_per_property() -> None:
    cell = {'x': 3, 'y': 4, 'food': 0.4, 'water': 1.0}
    changes = {'units': [], 'gone': [], 'cells': [cell], 'known': [], 'seat': {}}
    handed = Handed(5, Date(1, 1, 2, 'morning', 'spring'), [], changes, [])
    spoiled = {**handed.data(), 'changes': {**changes, 'cells': [{'x': 3, 'y': 4, 'food': 'alpha'}]}}
    placeless = {**handed.data(), 'changes': {**changes, 'cells': [{'x': 3, 'food': 0.4}]}}

    read = STREAM.validate_python(handed.data())

    assert isinstance(read, Update)
    assert read.changes.cells[0].model_dump() == {'x': 3, 'y': 4, 'food': 0.4, 'water': 1.0}
    for refused in (spoiled, placeless):
        with pytest.raises(ValidationError):
            STREAM.validate_python(refused)


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
