import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, Pass, StepResult, Vote, Window, council, decisions
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
AFTERNOON = SUMMER + 2
EVENING = SUMMER + 3
NIGHT = SUMMER + 4
DAY = 5
CALENDAR = ('day-started', 'month-started', 'season-started', 'year-started')
EAST = {'kind': 'move', 'towards': 'east'}
NORTHWARD = {'kind': 'move', 'towards': 'north'}
STAY = {'kind': 'stay-and-gather'}
ABSTAIN = {'kind': 'abstain'}


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def land(
    params: Params,
    at: tuple[int, int] = HOME,
    rows: tuple[tuple[str, ...], ...] = ROWS,
    stripped: list[tuple[int, int]] | None = None,
    parts: int = EVENING,
) -> Game:
    """
    A game with a player in the seat on a hand-made window on a summer evening, the cells of the band stripped
    where asked.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in rows], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    window = Window(0, WEST, NORTH, len(rows[0]), len(rows))
    game = Game(7, params, Streams(7), window, biomes, rivers, seated=True)
    game.clock.parts = parts
    for cell in stripped or []:
        for prop in ('food', 'water'):
            game.cells.lower(cell, prop, 0.9)
    game.band = bands.start(game, *at, game.day)
    return game


def sit(game: Game, *laid: tuple[dict[str, Any], int]) -> None:
    """
    A council of the day with the table given, as if the morning had opened it.
    """
    table = [{'proposal': proposal, 'votes': votes} for proposal, votes in laid]
    game.council = {'leader': council.leader(table), 'table': table}


def band(game: Game) -> bands.Band:
    assert game.band is not None
    return game.band


def told(result: StepResult) -> list[tuple[str, dict[str, Any]]]:
    return [(event.key, event.values) for event in result.events if event.key not in CALENDAR]


def vote(game: Game, proposal: Any, id: str = 'c-1') -> StepResult:
    game.submit(Vote(seat='player', proposal=proposal, id=id))
    return game.step()


def steps(game: Game, count: int) -> list[StepResult]:
    return [game.step() for _ in range(count)]


def said(results: list[StepResult]) -> list[tuple[str, dict[str, Any]]]:
    return [held for result in results for held in told(result)]


def judged(result: StepResult) -> list[tuple[str, dict[str, Any]]]:
    return [held for held in told(result) if held[0].startswith('proposal-')]


def test_the_voice_follows_the_document(params: Params) -> None:
    assert council.voice(params, 15, 50.0) == pytest.approx(3.75)
    assert council.voice(params, 15, 100.0) == pytest.approx(7.5)
    assert council.voice(params, 15, 10.0) == params.council.voice.least


def test_the_votes_of_the_example_lean_to_the_best_and_lie_by_the_largest_remainder() -> None:
    assert council.votes([0.5, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0], 14, 0.2) == [6, 1, 1, 4, 1, 1, 0, 0, 0]
    assert council.votes([0.5, 0.5], 3, 0.2) == [2, 1]
    assert council.votes([-0.1, 0.0], 14, 0.2) == [5, 9]
    assert council.votes([], 14, 0.2) == []
    assert sum(council.votes([0.1, 0.2, 0.3, 0.4, 0.5], 14, 0.2)) == 14


def test_a_small_spread_gives_nearly_everything_to_the_best() -> None:
    assert council.votes([0.6, 0.3], 14, 0.01) == [14, 0]
    assert council.votes([0.6, 0.3], 14, 100.0) == [7, 7]


def test_the_table_of_a_band_gives_every_other_one_vote_and_names_the_leader(params: Params) -> None:
    game = land(params, stripped=STRIPPED)

    laid = council.table(params, band(game), ERA)
    walks = decisions.options(params, band(game), ERA, allowed={'move'}, walking=True)
    best = max(walks, key=lambda held: held.score)

    assert sum(entry['votes'] for entry in laid) == band(game).population - 1
    assert all(entry['votes'] > 0 for entry in laid)
    assert council.leader(laid) == {'kind': 'move', 'towards': best.action['towards']}
    assert council.leader([]) is None
    assert council.key(None) == 'proposal-none'


def test_a_hungry_band_that_may_only_roam_still_weighs_every_way(params: Params) -> None:
    game = land(params)
    band(game).stores['forage'] = []

    kinds = {held.action['kind'] for held in decisions.options(params, band(game), ERA)}
    scored = council.score(params, band(game), ERA)

    assert 'move' not in kinds
    assert {'proposal-move-east', 'proposal-move-north', 'proposal-stay-and-gather'} < set(scored)


def test_the_decisions_of_the_example() -> None:
    laid = [
        {'proposal': STAY, 'votes': 6},
        {'proposal': NORTHWARD, 'votes': 1},
        {'proposal': EAST, 'votes': 4},
    ]

    assert council.decide(laid, EAST, 3.75) == (EAST, 7.75)
    assert council.decide(laid, NORTHWARD, 3.75) == (STAY, 4.75)
    assert council.decide(laid, STAY, 3.75) == (STAY, 9.75)


def test_a_tie_goes_to_the_player_and_among_the_others_to_the_fixed_order() -> None:
    assert council.decide([{'proposal': STAY, 'votes': 4}, {'proposal': EAST, 'votes': 2}], EAST, 2.0)[0] == EAST
    others = [{'proposal': STAY, 'votes': 3}, {'proposal': EAST, 'votes': 3}]
    assert council.decide(others, NORTHWARD, 2.0)[0] == STAY
    assert council.leader(others) == STAY


def test_the_evening_opens_the_council_and_the_seat_shows_its_table(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)

    opened = game.step()

    assert game.date.part == 'evening'
    assert game.council is not None
    assert told(opened)[-1] == ('council-opened', {'leader': council.key(game.council['leader'])})
    assert opened.changes['seat'] == {'council': game.council}
    assert game.seat['council'] == game.council
    assert game.counters.row()[-1] == 1


def test_a_settled_council_does_not_sit_and_the_day_is_the_players(params: Params) -> None:
    rows = (('grass', 'forest', 'forest'),)
    game = land(params, at=(WEST, NORTH), rows=rows, stripped=[(WEST, NORTH)], parts=AFTERNOON)

    agreed = game.step()

    assert told(agreed)[-1] == ('council-agreed', {'leader': 'proposal-stay-and-gather'})
    assert (game.council, game.asking, agreed.changes['seat']) == (None, [], {})
    assert game.answered == {'today': None, 'tomorrow': 'voted'}
    assert game.counters.row()[-1] == 0


@pytest.mark.parametrize(
    ('votes', 'spoken', 'settled'),
    [([11, 3], 3.75, True), ([8, 5], 3.75, False), ([7, 7], 0.5, False), ([14], 3.75, True), ([], 3.75, False)],
)
def test_a_council_is_settled_when_no_option_reaches_the_leader_with_the_players_voice(
    votes: list[int], spoken: float, settled: bool
) -> None:
    ways = ('east', 'west')[: len(votes)]
    laid = [
        {'proposal': {'kind': 'move', 'towards': way}, 'votes': held} for way, held in zip(ways, votes, strict=True)
    ]

    assert council.settled(laid, spoken) is settled


def test_the_council_rises_in_the_evening_tick_and_the_band_camps_through_it(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    band(game).fatigue = 0.5
    sit(game, (EAST, 14))

    result = vote(game, EAST)

    assert told(result) == [
        ('command-accepted', {'id': 'c-1'}),
        ('council-followed', {'proposal': 'proposal-move-east'}),
    ]
    assert result.changes['seat'] == {'council': None}
    assert band(game).action == {'kind': 'camp'}
    assert band(game).fatigue == pytest.approx(0.2)
    assert (band(game).intent, game.judgement, game.status) == ({'proposal': EAST}, None, 50.0)


def test_silence_and_abstaining_cost_two(params: Params) -> None:
    game = land(params)
    sit(game, (STAY, 14))
    silent = game.step()
    sit(game, (STAY, 14))
    abstained = vote(game, ABSTAIN)

    assert told(silent) == [('council-abstained', {'status': 48.0})]
    assert told(abstained)[-1] == ('council-abstained', {'status': 46.0})
    assert abstained.changes['seat'] == {'council': None, 'status': 46.0}


@pytest.mark.parametrize('answer', [STAY, ABSTAIN])
def test_a_band_that_the_council_keeps_on_its_cell_does_not_roam_away(params: Params, answer: dict[str, Any]) -> None:
    game = land(params, stripped=STRIPPED)
    sit(game, (STAY, 14))

    kinds = {result.units[0][4] for result in [vote(game, answer), *steps(game, DAY - 2)]}

    assert kinds <= {'gather', 'camp'}


def test_an_outvoted_player_pays_one_and_the_band_is_bound_to_the_winner(params: Params) -> None:
    game = land(params)
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))

    result = vote(game, NORTHWARD)

    assert told(result)[-1] == (
        'council-outvoted',
        {'proposal': 'proposal-move-north', 'winner': 'proposal-stay-and-gather', 'status': 49.0},
    )
    assert (band(game).intent, game.judgement) == ({'proposal': STAY}, None)


def test_the_first_example_turns_the_band_east_and_is_judged_at_the_next_council(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))
    promised = council.score(params, band(game), ERA)[council.key(STAY)]

    turned = vote(game, EAST, 'c-7')
    assert game.judgement is not None
    expected = game.judgement['expected']
    later = steps(game, DAY - 1)

    assert told(turned) == [
        ('command-accepted', {'id': 'c-7'}),
        ('council-turned', {'proposal': 'proposal-move-east', 'yes': 8.75, 'all': 17.75}),
    ]
    assert turned.units[0][4] == later[0].units[0][4] == 'camp'
    assert expected == pytest.approx(promised)
    assert [result.units[0][4] for result in later[1:]] == ['roam'] * 3
    assert judged(later[-1]) == [('proposal-worked', {'proposal': 'proposal-move-east', 'status': 54.0})]
    assert told(later[-1])[-1][0] == 'council-opened'
    assert band(game).intent is None
    assert game.judgement is None


def test_an_empty_seat_has_no_council_and_the_band_never_stops_for_one(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=NIGHT)
    game.seated = False

    night, morning = game.step(), game.step()

    assert game.council is None
    assert 'council-opened' not in [key for key, _ in told(night)]
    assert (night.changes['seat'], morning.changes['seat']) == ({}, {})
    assert morning.units[0][4] != 'camp'
    assert (game.status, game.asking) == (50.0, [])
    assert told(vote(game, STAY))[0] == ('command-refused', {'id': 'c-1', 'reason': 'refused-no-council'})


@pytest.mark.parametrize(
    ('proposal', 'reason'),
    [
        ('rest', 'refused-unknown-command'),
        ({'kind': 'rest'}, 'refused-unknown-command'),
        ({'kind': 'abstain', 'towards': 'east'}, 'refused-unknown-command'),
        ({'kind': 'move', 'towards': 'west'}, 'refused-no-such-direction'),
    ],
)
def test_a_vote_the_rules_do_not_take_is_refused(params: Params, proposal: Any, reason: str) -> None:
    game = land(params)
    sit(game, (STAY, 14))

    result = vote(game, proposal)

    assert told(result)[0] == ('command-refused', {'id': 'c-1', 'reason': reason})


def test_a_vote_without_a_council_or_a_second_vote_is_refused(params: Params) -> None:
    game = land(params)
    alone = vote(game, STAY)
    sit(game, (STAY, 14))
    game.submit(Vote(seat='player', proposal=STAY, id='c-2'))
    game.submit(Vote(seat='player', proposal=EAST, id='c-3'))

    twice = game.step()

    assert told(alone) == [('command-refused', {'id': 'c-1', 'reason': 'refused-no-council'})]
    assert told(twice)[:3] == [
        ('command-accepted', {'id': 'c-2'}),
        ('command-refused', {'id': 'c-3', 'reason': 'refused-already-voted'}),
        ('council-followed', {'proposal': 'proposal-stay-and-gather'}),
    ]


def test_a_banished_seat_is_refused_whatever_it_asks(params: Params) -> None:
    game = land(params)
    game.status = 0.0
    sit(game, (STAY, 14))
    game.submit(Pass(seat='player', id='c-1'))
    game.submit(Vote(seat='player', proposal=STAY, id='c-2'))

    result = game.step()

    reasons = [values['reason'] for key, values in told(result) if key == 'command-refused']

    assert reasons == ['refused-seat-banished'] * 2
    assert game.asking == []


@pytest.mark.parametrize(('answered', 'status'), [('voted', 35.0), ('silent', 35.0), (None, 50.0)])
def test_the_deaths_of_a_day_the_player_voted_or_kept_silent_on_cost_five_each(
    params: Params, answered: str | None, status: float
) -> None:
    game = land(params)
    band(game).stores = {}
    game.answered = {'today': answered, 'tomorrow': None}

    lost = said(steps(game, 2))

    blamed = [('seat-blamed', {'lost': 3, 'status': status})] if answered else []
    assert lost[lost.index(('people-lost', {'count': 3, 'cause': 'thirst'})) + 1 :] == blamed
    assert game.status == status


@pytest.mark.parametrize(('answered', 'status'), [('voted', 55.0), ('silent', 50.0), (None, 50.0)])
def test_a_birth_earns_five_only_on_a_day_the_player_voted_for(answered: str | None, status: float) -> None:
    fed = {'units.band.consumption_per_day.forage': 0.0, 'units.band.consumption_per_day.water': 0.0}
    game = land(load_params(overrides={**SMALL, **fed}))
    band(game).births = 0.99
    game.answered = {'today': answered, 'tomorrow': None}

    born = said(steps(game, 2))

    praised = [('seat-praised', {'born': 1, 'status': status})] if answered == 'voted' else []
    assert born == [('people-born', {'count': 1}), *praised]
    assert game.answered == {'today': None, 'tomorrow': None}


def test_an_intent_to_stay_never_moves(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=SUMMER + 1)
    band(game).intent = {'proposal': STAY}

    kinds = {result.units[0][4] for result in steps(game, DAY - 1)}

    assert kinds <= {'gather', 'camp'}


def test_a_move_goes_round_a_closed_way_and_ends_when_all_three_are_closed(params: Params) -> None:
    rows = (('grass', 'grass', 'water'), ('grass', 'grass', 'water'), ('grass', 'grass', 'grass'))
    game = land(params, at=(WEST + 1, NORTH + 1), rows=rows, stripped=STRIPPED, parts=SUMMER)
    band(game).intent = {'proposal': EAST}

    way = decisions.way(params, band(game), 'east', ERA)
    game.step()
    walked = band(game).action
    band(game).x, band(game).y = WEST + 1, NORTH
    band(game).intent = {'proposal': EAST}
    band(game).progress, band(game).target = 0.0, None
    ended = game.step()

    assert way == 'south-east'
    assert walked == {'kind': 'roam', 'towards': 'south-east'}
    assert band(game).intent is None
    assert told(ended)[0] == ('intent-ended', {'proposal': 'proposal-move-east'})


@pytest.mark.parametrize(
    ('proposal', 'lost', 'now', 'verdict'),
    [
        (EAST, {}, 0.3, 'worked'),
        (EAST, {}, 0.2, 'failed'),
        (EAST, {'hunger': 1}, 0.9, 'failed'),
        (EAST, {'encounter': 2, 'thirst': 1}, 0.9, 'disaster'),
        (STAY, {}, 0.5, 'worked'),
        (STAY, {}, 0.1, 'failed'),
        (STAY, {'encounter': 1}, 2.0, 'failed'),
        (STAY, {'encounter': 3}, 2.0, 'disaster'),
    ],
)
def test_the_verdicts_of_the_document(
    params: Params, proposal: dict[str, Any], lost: dict[str, int], now: float, verdict: str
) -> None:
    judgement = {'proposal': proposal, 'population': 15, 'expected': 0.3, 'lost': lost}

    assert council.verdict(params, judgement, now) == verdict


@pytest.mark.parametrize(
    ('proposal', 'verdict', 'amount'),
    [
        (EAST, 'worked', 4.0),
        (EAST, 'failed', -6.0),
        (EAST, 'disaster', -20.0),
        (STAY, 'worked', 3.0),
        (STAY, 'failed', -6.0),
        (STAY, 'disaster', -20.0),
    ],
)
def test_what_moves_status(params: Params, proposal: dict[str, Any], verdict: str, amount: float) -> None:
    assert council.amount(params, proposal, verdict) == amount


def test_the_worth_of_the_land_is_weighed_by_the_needs_given(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    hungry = {'hunger': 1.0, 'thirst': 0.0}
    stripped = council.worth(params, band(game), hungry)
    band(game).x = WEST + 3
    bands.look(game, band(game), game.day)

    assert council.worth(params, band(game), hungry) > stripped
    assert council.worth(params, band(game), {'hunger': 0.0, 'thirst': 0.0}) < 0


def test_staying_carried_fails_on_an_encounter_and_only_the_day_voted_for_is_blamed(params: Params) -> None:
    struck = load_params(
        overrides={
            **SMALL,
            'encounters.chance': 1.0,
            'encounters.kinds.predator.loss.min': 0.05,
            'encounters.kinds.predator.loss.max': 0.05,
            'biomes.forest.eras.band.properties.threat.base': 1.0,
            'council.judgement.disaster': 1.0,
        }
    )
    game = land(struck, at=(WEST + 3, NORTH + 1))
    sit(game, (EAST, 2))

    results = [vote(game, STAY), *steps(game, DAY - 1)]
    taken = sum(values['lost'] for key, values in said(results) if key == 'encounter')
    blamed = sum(values['lost'] for key, values in said(results) if key == 'seat-blamed')
    verdict = ('proposal-failed', {'proposal': 'proposal-stay-and-gather', 'lost': taken, 'status': 29.0})

    assert said(results)[1][0] == 'council-turned'
    assert (taken, blamed) == (4, 3)
    assert judged(results[-1]) == [verdict]


def test_status_is_held_at_a_hundred(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    game.status = 99.0
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))

    results = [vote(game, EAST), *steps(game, DAY - 1)]

    assert judged(results[-1]) == [('proposal-worked', {'proposal': 'proposal-move-east', 'status': 100.0})]
    assert results[-1].changes['seat']['status'] == 100.0


def test_banishment_by_silence_ends_the_game_and_spares_the_band(params: Params) -> None:
    game = land(params)
    game.status = 2.0
    sit(game, (STAY, 14))

    result = game.step()
    later = vote(game, STAY, 'c-2')

    assert told(result) == [('council-abstained', {'status': 0.0}), ('seat-banished', {})]
    assert (game.over, game.outcome, game.status) == (True, 'banished', 0.0)
    assert game.band is not None
    assert told(later) == [('command-refused', {'id': 'c-2', 'reason': 'refused-seat-banished'})]


def test_the_seat_judgement_and_intent_are_in_the_snapshot_and_restore_to_the_same_verdict(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))
    vote(game, EAST)
    steps(game, 2)

    snapshot = json.loads(json.dumps(game.snapshot(), default=lambda grid: grid.tolist()))
    copy = Game.restore(snapshot)

    assert snapshot['seat'] == {'name': 'player', 'unit': 1, 'status': 50.0, 'seated': True, 'council': None}
    assert snapshot['judgement']['proposal'] == EAST
    assert snapshot['units'][0]['intent'] == {'proposal': EAST}
    assert copy.state_hash() == game.state_hash()
    assert [told(result) for result in steps(copy, 2)] == [told(result) for result in steps(game, 2)]
    assert copy.state_hash() == game.state_hash()
    assert copy.council == game.council is not None


def test_a_year_of_votes_gives_the_same_hashes_twice(params: Params) -> None:
    said_here = [EAST, NORTHWARD, STAY, ABSTAIN, {'kind': 'move', 'towards': 'south-west'}]

    def year(game: Game) -> tuple[list[str], float, int]:
        found = []
        for tick in range(params.time.parts_per_day * params.time.days_per_year):
            if game.council is not None and tick % 3:
                game.submit(Vote(seat='player', proposal=said_here[tick // 5 % len(said_here)]))
            found.append(game.step().hash)
            if game.over:
                break
        return found, game.status, int(game.counters.row()[-1])

    first = year(Game.create(seed=7, params=params, seated=True))

    assert first == year(Game.create(seed=7, params=params, seated=True))
    assert first[2] > 0
    assert first[1] != params.council.status.start
