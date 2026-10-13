import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import CallCouncil, Game, Pass, StepResult, Window, council, decisions
from dominion_theory.engine import band as bands
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
}
ERA = 'band'
WEST = 100
NORTH = 50
ROWS = (('grass', 'grass', 'forest', 'forest', 'forest', 'forest'),) * 3
HOME = (WEST, NORTH + 1)
STRIPPED = [(x, y) for x in (WEST, WEST + 1) for y in range(NORTH, NORTH + 3)]
SUMMER = 100
NIGHT = SUMMER + 4
CALENDAR = ('day-started', 'month-started', 'season-started', 'year-started')
EAST = {'kind': 'move', 'towards': 'east'}
REST = {'kind': 'rest'}
STAY = {'kind': 'stay-and-gather'}
JUDGED = 15
MOVE_HOLDS = 5
GAP = 10


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def land(
    params: Params,
    at: tuple[int, int] = HOME,
    rows: tuple[tuple[str, ...], ...] = ROWS,
    stripped: list[tuple[int, int]] | None = None,
    parts: int = SUMMER,
) -> Game:
    """
    A game on a hand-made window in summer, the cells of the band stripped where asked.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in rows], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    game = Game(7, params, Streams(7), Window(0, WEST, NORTH, len(rows[0]), len(rows)), biomes, rivers)
    game.clock.parts = parts
    for cell in stripped or []:
        for prop in ('food', 'water'):
            game.cells.lower(cell, prop, 0.9)
    game.band = bands.start(game, *at, game.day)
    return game


def band(game: Game) -> bands.Band:
    assert game.band is not None
    return game.band


def told(result: StepResult) -> list[tuple[str, dict[str, Any]]]:
    return [(event.key, event.values) for event in result.events if event.key not in CALENDAR]


def call(game: Game, proposal: Any, id: str = 'c-1') -> StepResult:
    game.submit(CallCouncil(seat='player', proposal=proposal, id=id))
    return game.step()


def steps(game: Game, count: int) -> list[StepResult]:
    return [game.step() for _ in range(count)]


def said(results: list[StepResult]) -> list[tuple[str, dict[str, Any]]]:
    return [held for result in results for held in told(result)]


def test_the_voice_and_the_agreement_needed_follow_the_document(params: Params) -> None:
    def needed(status: float) -> float:
        voice = council.voice(params, 15, status)
        return (14 + voice) / 2 / 14 - voice / 14

    assert council.voice(params, 15, 50.0) == pytest.approx(3.75)
    assert council.voice(params, 15, 100.0) == pytest.approx(7.5)
    assert council.voice(params, 15, 10.0) == params.council.voice.least
    assert (round(needed(50.0), 2), round(needed(100.0), 2)) == (0.37, 0.23)


def test_the_second_example_of_the_document_is_voted_down(params: Params) -> None:
    agreement = council.agreement(0.1, 0.6)
    voice = council.voice(params, 15, 50.0)

    yes, every = agreement * 14 + voice, 14 + voice

    assert agreement == pytest.approx(1 / 6)
    assert yes == pytest.approx(6.083, abs=1e-3)
    assert every == 17.75
    assert not yes > every / 2


@pytest.mark.parametrize(
    ('proposed', 'best', 'agreement'),
    [(0.7, 0.6, 1.0), (0.6, 0.6, 1.0), (-0.2, -0.2, 1.0), (-0.3, -0.2, 0.0), (-0.1, 0.5, 0.0), (0.3, 0.6, 0.5)],
)
def test_agreement_is_held_between_none_and_all(proposed: float, best: float, agreement: float) -> None:
    assert council.agreement(proposed, best) == pytest.approx(agreement)


def test_the_first_example_of_the_document_passes_walks_east_and_works(params: Params) -> None:
    game = land(params, stripped=STRIPPED)

    first = call(game, EAST, 'c-7')
    walked = band(game).action
    held = band(game).intent
    later = steps(game, JUDGED - 1)

    assert told(first) == [
        ('command-accepted', {'id': 'c-7'}),
        ('council-accepted', {'proposal': 'proposal-move-east', 'yes': 17.75, 'all': 17.75}),
    ]
    assert first.changes['seat'] == {'council_from': GAP}
    assert walked == {'kind': 'move', 'towards': 'east'}
    assert held == {'proposal': EAST, 'until': MOVE_HOLDS}
    assert band(game).intent is None
    assert told(later[-1]) == [('proposal-worked', {'proposal': 'proposal-move-east', 'status': 54.0})]
    assert later[-1].changes['seat'] == {'status': 54.0}
    assert [held for result in later[:-1] for held in told(result) if held[0].startswith('proposal-')] == []
    assert game.counters.names[-2:] == ('status', 'councils')
    assert later[-1].counters[-2:] == [54.0, 1]


def own(params: Params, game: Game) -> dict[str, Any]:
    best = max(decisions.options(params, band(game), game.date.part, ERA), key=lambda held: held.score)
    if best.action['kind'] == 'move':
        return {'kind': 'move', 'towards': best.action['towards']}
    return REST if best.action['kind'] == 'camp' else STAY


@pytest.mark.parametrize(
    ('stripped', 'parts', 'fed', 'kind'),
    [(STRIPPED, SUMMER, False, 'move'), (None, SUMMER, False, 'stay-and-gather'), (None, NIGHT, True, 'rest')],
)
def test_a_proposal_the_band_would_choose_itself_always_passes(
    params: Params, stripped: list[tuple[int, int]] | None, parts: int, fed: bool, kind: str
) -> None:
    game = land(params, stripped=stripped, parts=parts)
    if fed:
        band(game).stores = {'forage': [[0.0, 45.0]], 'water': [[0.0, 45.0]]}
    proposal = own(params, game)

    for status in (1.0, 50.0):
        yes, every = council.vote(params, band(game), proposal, status, game.date.part, ERA)
        assert yes == every
    assert proposal['kind'] == kind
    assert told(call(game, proposal))[1][0] == 'council-accepted'


def test_a_council_too_soon_is_refused_and_starts_no_gap(params: Params) -> None:
    game = land(params)
    call(game, REST)

    refused = call(game, REST, 'c-2')
    steps(game, GAP - 3)
    still = call(game, REST, 'c-3')

    assert told(refused) == [('command-refused', {'id': 'c-2', 'reason': 'refused-council-too-soon'})]
    assert refused.changes['seat'] == {}
    assert told(still)[0][1]['reason'] == 'refused-council-too-soon'
    assert game.council_from == GAP


def test_a_council_while_a_proposal_waits_for_its_judgement_is_refused(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    call(game, EAST)
    steps(game, GAP - 1)

    refused = call(game, REST, 'c-2')

    assert game.judgement is not None
    assert told(refused) == [('command-refused', {'id': 'c-2', 'reason': 'refused-proposal-pending'})]


def test_a_way_closed_on_three_sides_is_refused_and_the_next_council_may_follow(params: Params) -> None:
    game = land(params)

    refused = call(game, {'kind': 'move', 'towards': 'west'})
    accepted = call(game, {'kind': 'move', 'towards': 'north-west'}, 'c-2')

    assert told(refused) == [('command-refused', {'id': 'c-1', 'reason': 'refused-no-such-direction'})]
    assert (refused.changes['seat'], told(accepted)[0]) == ({}, ('command-accepted', {'id': 'c-2'}))


def test_a_proposal_the_rules_do_not_know_is_an_unknown_command(params: Params) -> None:
    game = land(params)

    refused = call(game, 'rest')

    assert told(refused) == [('command-refused', {'id': 'c-1', 'reason': 'refused-unknown-command'})]


def test_a_banished_seat_is_refused_whatever_it_asks(params: Params) -> None:
    game = land(params)
    game.status = 0.0
    game.submit(Pass(seat='player', id='c-1'))
    game.submit(CallCouncil(seat='player', proposal=REST, id='c-2'))

    result = game.step()

    assert [values['reason'] for _, values in told(result)] == ['refused-seat-banished'] * 2


def test_a_rest_holds_while_the_food_runs_out_and_always_works(params: Params) -> None:
    game = land(params, parts=NIGHT)
    call(game, REST)
    band(game).stores = {}

    results = steps(game, 9)

    assert {result.units[0][4] for result in results} == {'camp'}
    assert ('band-state-began', {'state': 'state-thirst'}) in said(results)
    assert told(results[-1])[-1] == ('proposal-worked', {'proposal': 'proposal-rest', 'status': 52.0})
    assert band(game).intent is None


def test_an_intent_to_stay_never_moves_and_one_to_rest_never_gathers(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    hungry = land(params)
    band(game).intent = {'proposal': STAY, 'until': 100}
    band(hungry).intent = {'proposal': REST, 'until': 100}

    kinds = {result.units[0][4] for result in steps(game, 10)}
    rested = {result.units[0][4] for result in steps(hungry, 10)}

    assert 'move' not in kinds
    assert rested == {'camp'}


def test_a_move_goes_round_a_closed_way_and_ends_when_all_three_are_closed(params: Params) -> None:
    rows = (('grass', 'grass', 'water'), ('grass', 'grass', 'water'), ('grass', 'grass', 'grass'))
    game = land(params, at=(WEST + 1, NORTH + 1), rows=rows, stripped=STRIPPED)
    band(game).intent = {'proposal': EAST, 'until': 100}

    way = decisions.way(params, band(game), 'east', ERA)
    game.step()
    walked = band(game).action
    band(game).x, band(game).y = WEST + 1, NORTH
    band(game).intent = {'proposal': EAST, 'until': 100}
    band(game).progress, band(game).target = 0.0, None
    ended = game.step()

    assert way == 'south-east'
    assert walked == {'kind': 'move', 'towards': 'south-east'}
    assert band(game).intent is None
    assert told(ended)[0] == ('intent-ended', {'proposal': 'proposal-move-east'})


@pytest.mark.parametrize(
    ('proposal', 'lost', 'now', 'verdict'),
    [
        (EAST, {}, 1.0, 'worked'),
        (EAST, {}, 0.7, 'failed'),
        (EAST, {'hunger': 1}, 2.0, 'failed'),
        (EAST, {'encounter': 2, 'thirst': 1}, 2.0, 'disaster'),
        (REST, {'hunger': 5}, 0.0, 'worked'),
        (STAY, {'hunger': 5}, 0.0, 'worked'),
        (STAY, {'encounter': 1}, 2.0, 'failed'),
        (STAY, {'encounter': 3}, 2.0, 'disaster'),
    ],
)
def test_the_verdicts_of_the_document(
    params: Params, proposal: dict[str, Any], lost: dict[str, int], now: float, verdict: str
) -> None:
    judgement = {'proposal': proposal, 'closes': 0, 'population': 15, 'supply': 1.0, 'lost': lost}

    assert council.verdict(params, judgement, now) == verdict


@pytest.mark.parametrize(
    ('proposal', 'verdict', 'amount'),
    [
        (EAST, 'worked', 4.0),
        (EAST, 'failed', -6.0),
        (EAST, 'disaster', -20.0),
        (REST, 'worked', 2.0),
        (STAY, 'worked', 3.0),
        (STAY, 'failed', -6.0),
        (STAY, 'disaster', -20.0),
    ],
)
def test_what_moves_status(params: Params, proposal: dict[str, Any], verdict: str, amount: float) -> None:
    assert council.amount(params, proposal, verdict) == amount


def test_supply_is_the_lesser_of_food_and_water_held_at_the_cap(params: Params) -> None:
    game = land(params)

    full = council.supply(params, band(game))
    band(game).stores = {'forage': [[0.0, 7.5]], 'water': [[0.0, 60.0]]}

    assert (full, council.supply(params, band(game))) == (1.0, 0.5)
    band(game).stores = {'forage': [[0.0, 90.0]], 'water': [[0.0, 90.0]]}
    assert council.supply(params, band(game)) == 2.0


def test_staying_fails_on_an_encounter(params: Params) -> None:
    struck = load_params(
        overrides={
            **SMALL,
            'encounters.chance': 1.0,
            'encounters.kinds.predator.loss.min': 0.05,
            'encounters.kinds.predator.loss.max': 0.05,
            'council.judgement.disaster': 1.0,
        }
    )
    game = land(struck, at=(WEST + 3, NORTH + 1))

    results = [call(game, STAY), *steps(game, 9)]
    taken = sum(values['lost'] for key, values in said(results) if key == 'encounter')

    assert said(results)[1][0] == 'council-accepted'
    assert taken > 0
    assert told(results[-1])[-1] == (
        'proposal-failed',
        {'proposal': 'proposal-stay-and-gather', 'lost': taken, 'status': 44.0},
    )


def test_status_is_held_at_a_hundred(params: Params) -> None:
    game = land(params, parts=NIGHT)
    game.status = 99.0
    call(game, REST)

    results = steps(game, 9)

    assert told(results[-1])[-1] == ('proposal-worked', {'proposal': 'proposal-rest', 'status': 100.0})
    assert results[-1].changes['seat'] == {'status': 100.0}


def test_banishment_ends_the_game_and_spares_the_band(params: Params) -> None:
    game = land(params)
    game.status = 2.0

    result = call(game, {'kind': 'move', 'towards': 'south'})
    later = call(game, REST, 'c-2')

    assert [key for key, _ in told(result)] == ['command-accepted', 'council-declined', 'seat-banished']
    assert told(result)[1][1]['status'] == 0.0
    assert (game.over, game.outcome, game.status) == (True, 'banished', 0.0)
    assert game.band is not None
    assert told(later) == [('command-refused', {'id': 'c-2', 'reason': 'refused-seat-banished'})]


def test_the_seat_judgement_and_intent_are_in_the_snapshot_and_restore_to_the_same_verdict(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    call(game, EAST)
    steps(game, 3)

    snapshot = json.loads(json.dumps(game.snapshot(), default=lambda grid: grid.tolist()))
    copy = Game.restore(snapshot)

    assert snapshot['seat'] == {'name': 'player', 'unit': 1, 'status': 50.0, 'council_from': GAP}
    assert snapshot['judgement']['proposal'] == EAST
    assert snapshot['units'][0]['intent'] == {'proposal': EAST, 'until': MOVE_HOLDS}
    assert copy.state_hash() == game.state_hash()
    assert [told(result) for result in steps(copy, JUDGED - 4)] == [told(result) for result in steps(game, JUDGED - 4)]
    assert copy.state_hash() == game.state_hash()


def test_a_year_with_councils_gives_the_same_hashes_twice(params: Params) -> None:
    said_here = [EAST, REST, STAY, {'kind': 'move', 'towards': 'south-west'}]

    def year(game: Game) -> tuple[list[str], float, int]:
        found = []
        for tick in range(params.time.parts_per_day * params.time.days_per_year):
            if tick % 37 == 0:
                game.submit(CallCouncil(seat='player', proposal=said_here[tick // 37 % len(said_here)]))
            found.append(game.step().hash)
        return found, game.status, int(game.counters.row()[-1])

    first = year(Game.create(seed=7, params=params))

    assert first == year(Game.create(seed=7, params=params))
    assert first[2] > 0
