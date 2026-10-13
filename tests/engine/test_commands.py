from dominion_theory.engine import CallCouncil, Command, Pass
from dominion_theory.engine.commands import BUILT


def test_pass_and_the_council_are_built() -> None:
    assert {'pass', 'call-council'} == BUILT


def test_envelope_is_the_id_the_kind_and_the_rest() -> None:
    assert Pass(seat='player', id='c-1').envelope() == {'id': 'c-1', 'kind': 'pass'}
    assert CallCouncil(seat='player', proposal={'kind': 'move', 'towards': 'east'}, id='c-2').envelope() == {
        'id': 'c-2',
        'kind': 'call-council',
        'proposal': {'kind': 'move', 'towards': 'east'},
    }


def test_command_is_read_back_from_its_envelope() -> None:
    sent = CallCouncil(seat='player', proposal='rest', id='c-2')

    read = Command.read('player', sent.envelope())

    assert (read.seat, read.kind, read.id, read.fields) == ('player', 'call-council', 'c-2', {'proposal': 'rest'})
    assert read.envelope() == sent.envelope()


def test_command_without_an_id_can_be_named() -> None:
    named = Pass(seat='player').named('player-1')

    assert Pass(seat='player').id is None
    assert named.envelope() == {'id': 'player-1', 'kind': 'pass'}


def test_envelope_with_no_kind_is_still_a_command() -> None:
    assert Command.read('player', {'id': 'c-3'}).kind == ''
