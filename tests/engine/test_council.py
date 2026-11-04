import json
from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, Pass, StepResult, Vote, Window, council, decisions
from dominion_theory.engine import band as bands
from dominion_theory.engine.game import _Tick
from dominion_theory.engine.stock import Stock
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.decisions.horizon': 0,
    # Without the unknown nearby a dearer distance of known land keeps a fed band on stripped land.
    'units.band.decisions.distance_known': 0.25,
    # A band that never stands for its stores walks its plan; RHYTHM below brings the stands back.
    'units.band.plan.march': 0.0,
    'units.band.plan.stock': 0.0,
    'units.band.unease.gain': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
    'units.band.people.injury.per_day': 0.0,
    'units.band.people.age.per_year': 0.0,
    'units.band.people.stages.adult.dies.frailty': 0.0,
}
ERA = 'band'
WEST = 100
NORTH = 50
ROWS = (('grass', 'grass', 'forest', 'forest', 'forest', 'forest'),) * 3
HOME = (WEST, NORTH + 1)
MEADOWS = [(WEST + 1, y) for y in range(NORTH, NORTH + 3)]
STRIPPED = [(x, y) for x in (WEST, WEST + 1) for y in range(NORTH, NORTH + 3)]
SUMMER = 100
AFTERNOON = SUMMER + 2
EVENING = SUMMER + 3
NIGHT = SUMMER + 4
DAY = 5
CALENDAR = ('day-started', 'month-started', 'season-started', 'year-started')
EAST = council.going('roam', (WEST + 2, NORTH + 1))
NORTHWARD = council.going('roam', (WEST, NORTH))
STAY = {'kind': 'camp'}
ABSTAIN = {'kind': 'abstain'}
QUIET = {'first': False, 'death': 0, 'encounter': False, 'found': False, 'spent': False, 'season': False}
# A morning in the middle of the winter, and the first morning of the second year.
WINTER = 75 * DAY
SPRING = 100 * DAY


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
    where asked; the band knows every skill.
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
    game.band = bands.start(game, *at, game.day, game.streams['people'])
    game.band.members = bands.adults(game.band.population)
    game.band.lore['known'] = list(params.skills)
    game.band.changed()
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


def intent(game: Game) -> dict[str, Any]:
    held = band(game).intent
    assert held is not None
    return held


def bind(game: Game, proposal: dict[str, Any]) -> None:
    game._bind(band(game), proposal)


def wintering(game: Game, until: int = 10_000) -> None:
    """
    The band bound to a winter camp on its cell, whatever the season.
    """
    band(game).intent = {'proposal': STAY, 'until': until, 'leg': None, 'standing': False, 'winter': True}


def aimed(laid: council.Table, proposal: dict[str, Any] | None) -> tuple[int, int]:
    entry = next(entry for entry in laid if entry['proposal'] == proposal)
    return entry['to']['x'], entry['to']['y']


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

    laid = council.table(params, band(game), ERA, game.inside)
    leader = council.leader(laid)
    going = [entry for entry in laid if entry['proposal']['kind'] != 'camp']

    assert sum(entry['votes'] for entry in laid) == bands.voters(params, band(game)) - 1 == 14
    assert all(entry['votes'] > 0 for entry in laid)
    assert all(entry['key'] == council.key(entry['proposal'], band(game)) for entry in laid)
    assert next(entry['score'] for entry in laid if entry['proposal'] == leader) == max(e['score'] for e in laid)
    assert going and all(
        entry['offset'] == {'dx': entry['to']['x'] - WEST, 'dy': entry['to']['y'] - NORTH - 1}
        and set(entry['expect']) == {'food', 'water', 'threat'}
        for entry in going
    )
    days = council.score(params, band(game), ERA, game.inside)
    kept = [round(held, 4) for proposal, held, _ in days if any(entry['proposal'] == proposal for entry in laid)]
    assert [entry['score'] for entry in laid] == kept
    assert council.leader([]) is None
    assert council.key(None) == 'proposal-none'


def test_a_hungry_band_that_may_only_roam_still_weighs_every_way(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    band(game).stores['forage'] = []

    kinds = {held.action['kind'] for held in decisions.options(params, band(game), ERA)}
    days = council.score(params, band(game), ERA, game.inside)

    assert 'move' not in kinds
    assert days[0][0] == STAY
    assert len(days) > 1 and all(proposal['kind'] == 'roam' for proposal, _, _ in days[1:])
    assert len({at for _, _, at in days}) == len(days)


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
    leader = game._key(band(game), game.council['leader'])
    assert told(opened)[-1] == ('council-opened', {'leader': leader, 'occasion': 'occasion-first'})
    assert opened.changes['seat'] == {'council': game.council}
    assert game.seat['council'] == game.council
    assert game.council['voice'] == pytest.approx(3.75)
    assert councils(game) == 1


def councils(game: Game) -> float:
    return dict(zip(game.counters.names, game.counters.row(), strict=True))['councils']


def quiet(game: Game) -> council.Proposal | None:
    """
    Nothing happened since the last council, and the band is bound to what it leans to: no occasion holds.
    """
    game.since = dict(QUIET)
    leader = council.leader(council.table(game.params, band(game), ERA, game.inside))
    game._bind(band(game), leader)
    return leader


def test_an_evening_with_no_occasion_calls_no_council_and_the_decision_stands(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    leader = quiet(game)

    evening = game.step()

    assert game.council is None
    assert [key for key, _ in told(evening) if key.startswith('council-')] == []
    assert intent(game)['proposal'] == leader


@pytest.mark.parametrize(
    ('since', 'occasion'),
    [
        ({'first': True}, 'first'),
        ({'death': 2}, 'death'),
        ({'encounter': True}, 'encounter'),
        ({'found': True}, 'found'),
        ({'spent': True}, 'spent'),
        ({'season': True}, 'season'),
        ({'death': 1, 'spent': True}, 'death'),
    ],
)
def test_what_happened_since_the_last_council_calls_it(params: Params, since: dict[str, Any], occasion: str) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    quiet(game)
    game.since.update(since)

    opened = game.step()

    assert told(opened)[-1][1]['occasion'] == f'occasion-{occasion}'
    assert game.since == QUIET


def test_the_term_of_the_plan_over_calls_the_council(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    quiet(game)
    intent(game)['until'] = game.day

    assert told(game.step())[-1][1]['occasion'] == 'occasion-term'


@pytest.mark.parametrize(
    ('stores', 'state', 'occasion'),
    [({'dried': 200.0}, 'thirst', 'occasion-thirst'), ({'water': 200.0}, 'starvation', 'occasion-hunger')],
)
def test_the_council_names_the_need_the_stores_no_longer_cover(
    params: Params, stores: dict[str, float], state: str, occasion: str
) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    quiet(game)
    bind(game, STAY)
    band(game).stores = Stock({name: [[float(game.day), amount]] for name, amount in stores.items()})
    band(game).states = [state]

    assert told(game.step())[-1][1]['occasion'] == occasion


@pytest.mark.parametrize(('dying', 'occasions'), [(False, []), (True, ['occasion-hunger'])])
def test_hunger_on_a_plan_calls_the_council_only_once_a_member_dies_tonight(
    params: Params, dying: bool, occasions: list[str]
) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    quiet(game)
    bind(game, EAST)
    band(game).states = ['tiredness']
    band(game).stores = Stock()
    if dying:
        band(game).members[1].hungry = 1.0
    band(game).changed()

    evening = game.step()

    called = [values['occasion'] for key, values in told(evening) if key in ('council-opened', 'council-agreed')]
    assert called == occasions


def test_a_band_on_its_way_does_not_turn_for_another_wish(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    quiet(game)
    bind(game, council.going('roam', (WEST, NORTH + 2)))

    evening = game.step()

    assert game.council is None
    assert [key for key, _ in told(evening) if key.startswith('council-')] == []


def test_a_settled_council_does_not_sit_and_the_day_belongs_to_nobody(params: Params) -> None:
    rows = (('grass', 'forest', 'forest'),)
    game = land(params, at=(WEST, NORTH), rows=rows, stripped=[(WEST, NORTH)], parts=AFTERNOON)
    game.answered = {'today': 'voted', 'tomorrow': 'voted'}

    agreed = game.step()

    assert told(agreed)[-1] == ('council-agreed', {'leader': 'proposal-camp', 'occasion': 'occasion-first'})
    assert (game.council, game.asking, agreed.changes['seat']) == (None, [], {})
    assert game.answered == {'today': 'voted', 'tomorrow': None}
    assert councils(game) == 0


def test_the_deaths_of_the_day_after_a_settled_council_cost_the_seat_nothing(params: Params) -> None:
    rows = (('grass', 'forest', 'forest'),)
    game = land(params, at=(WEST, NORTH), rows=rows, stripped=[(WEST, NORTH)], parts=AFTERNOON)
    game.answered = {'today': 'voted', 'tomorrow': 'voted'}
    game.step()
    steps(game, DAY)
    today = game.answered['today']
    band(game).stores = Stock()
    for member in band(game).members[1:4]:
        member.thirsty = 1.5

    lost = said(steps(game, 2))

    assert today is None
    assert ('people-lost', {'count': 3, 'cause': 'thirst'}) in lost
    assert [key for key, _ in lost if key == 'seat-blamed'] == []


@pytest.mark.parametrize(
    ('votes', 'spoken', 'settled'),
    [([11, 3], 3.75, True), ([8, 5], 3.75, False), ([7, 7], 0.5, False), ([14], 3.75, True), ([], 3.75, False)],
)
def test_a_council_is_settled_when_no_option_reaches_the_leader_with_the_players_voice(
    votes: list[int], spoken: float, settled: bool
) -> None:
    ways = (EAST, NORTHWARD)[: len(votes)]
    laid = [{'proposal': way, 'votes': held} for way, held in zip(ways, votes, strict=True)]

    assert council.settled(laid, spoken) is settled


def test_the_council_rises_in_the_evening_tick_and_the_band_camps_through_it(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    band(game).fatigue = 0.5
    sit(game, (EAST, 14))

    result = vote(game, EAST)

    assert told(result) == [
        ('command-accepted', {'id': 'c-1'}),
        ('council-followed', {'proposal': 'proposal-roam-e'}),
    ]
    assert result.changes['seat'] == {'council': None}
    assert band(game).action == {'kind': 'camp'}
    assert band(game).fatigue == pytest.approx(0.2)
    assert band(game).intent == {
        'proposal': EAST,
        'until': game.day + 10,
        'leg': {'x': WEST + 2, 'y': NORTH + 1},
        'standing': False,
        'winter': False,
    }
    assert (game.judgement, game.status) == (None, 50.0)


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
        {'proposal': 'proposal-roam-n', 'winner': 'proposal-camp', 'status': 49.0},
    )
    assert intent(game)['proposal'] == STAY
    assert game.judgement is None


def test_the_first_example_turns_the_band_east_and_is_judged_when_it_arrives(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))
    promised = next(
        held for proposal, held, _ in council.score(params, band(game), ERA, game.inside) if proposal == STAY
    )

    turned = vote(game, EAST, 'c-7')
    game.since['first'] = False
    assert game.judgement is not None
    expected = game.judgement['expected']
    later = steps(game, 3 * DAY)

    assert told(turned) == [
        ('command-accepted', {'id': 'c-7'}),
        ('council-turned', {'proposal': 'proposal-roam-e', 'yes': 8.75, 'all': 17.75}),
    ]
    assert turned.units[0][4] == later[0].units[0][4] == 'camp'
    assert expected == pytest.approx(promised)
    assert [result.units[0][4] for result in later[1:4]] == ['roam'] * 3
    reached = ('plan-ended', {'proposal': 'proposal-roam', 'why': 'reached'})
    at = next(at for at, result in enumerate(later) if reached in told(result))
    assert judged(later[at]) == [('proposal-worked', {'proposal': 'proposal-roam-e', 'status': 54.0})]
    assert [held for result in later for held in judged(result)] == judged(later[at])
    assert any(values.get('occasion') == 'occasion-spent' for _, values in said(later[at:]))
    assert game.judgement is None


def test_a_council_judges_the_turned_plan_in_force_before_its_table() -> None:
    params = load_params(overrides={**SMALL, 'council.spread': 100.0})
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    going = council.going('roam', (WEST + 1, NORTH + 1))
    quiet(game)
    bind(game, going)
    band(game).states = ['tiredness']
    game.since['death'] = 1
    needs = decisions.needs(params, band(game))
    promised = {'expected': -9.0, 'before': -9.0, 'unease': 0.0}
    game.judgement = {'proposal': going, 'key': 'proposal-roam-e', 'needs': needs, **promised}

    opened = game.step()

    assert [key for key, _ in told(opened)][-2:] == ['proposal-worked', 'council-opened']
    assert game.judgement is None


def test_the_band_remembers_the_land_its_last_decision_left_through_it_and_for_the_days_of_memory(
    params: Params,
) -> None:
    game = land(params, stripped=STRIPPED)
    band(game).x = WEST + 1
    game._bind(band(game), EAST)
    taken = band(game).decision
    game._bind(band(game), EAST)
    memory = params.days(params.council.memory)

    assert band(game).decision == taken == {'proposal': EAST, 'from': [WEST + 1, NORTH + 1], 'day': game.day}
    assert council.behind(params, band(game), game.day + memory + 50) == (WEST + 1, NORTH + 1)
    band(game).intent = None
    assert council.behind(params, band(game), game.day + memory) == (WEST + 1, NORTH + 1)
    assert council.behind(params, band(game), game.day + memory + 1) is None


def test_the_council_does_not_send_the_band_back_while_other_land_is_as_good(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    laid = council.table(params, band(game), ERA, game.inside)
    first = council.leader(laid)
    assert first is not None and first['kind'] == 'roam'

    again = council.table(params, band(game), ERA, game.inside, behind=aimed(laid, first))
    then = council.leader(again)

    assert then is not None and then['kind'] == 'roam'
    assert aimed(again, then) != aimed(laid, first)


def test_a_starving_band_goes_back_to_the_land_it_left_when_nothing_else_feeds_it(params: Params) -> None:
    left = (WEST + 1, NORTH)
    others = [(x, y) for x in range(WEST, WEST + 6) for y in range(NORTH, NORTH + 3) if (x, y) != left]
    game = land(params, stripped=others)
    held = starving(game)
    held.visited[left] = game.day

    laid = council.table(params, held, ERA, game.inside, behind=left)

    assert aimed(laid, council.leader(laid)) == left


def test_the_go_in_force_keeps_its_momentum_and_a_go_back_loses_a_day(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    days = council.score(params, band(game), ERA, game.inside, (EAST,))
    bind(game, EAST)

    going = council.remembered(params, band(game), days, None)
    band(game).intent = None
    back = council.remembered(params, band(game), days, (WEST + 2, NORTH + 1))

    def moved(found: list[council.Day]) -> list[float]:
        return [round(held - day, 9) for (_, held, _), (_, day, _) in zip(found, days, strict=True)]

    assert any(proposal == EAST for proposal, _, _ in days)
    assert moved(going) == [0.1 if proposal == EAST else 0.0 for proposal, _, _ in days]
    gone = [-0.9 if proposal['kind'] == 'roam' and at == (WEST + 2, NORTH + 1) else 0.0 for proposal, _, at in days]
    assert moved(back) == gone


def test_an_empty_seat_has_no_council_and_the_leader_binds_the_band(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    game.seated = False

    evening = game.step()

    laid = council.table(params, band(game), ERA, game.inside)
    assert game.council is None
    assert [key for key, _ in told(evening) if key.startswith('council-')] == []
    assert evening.changes['seat'] == {}
    assert intent(game)['proposal'] in [entry['proposal'] for entry in laid]
    assert (game.status, game.asking, councils(game)) == (50.0, [], 0)
    assert told(vote(game, STAY))[0] == ('command-refused', {'id': 'c-1', 'reason': 'refused-no-council'})


@pytest.mark.parametrize(
    ('proposal', 'reason'),
    [
        ('rest', 'refused-unknown-command'),
        ({'kind': 'rest'}, 'refused-unknown-command'),
        ({'kind': 'abstain', 'towards': 'east'}, 'refused-unknown-command'),
        ({'kind': 'move', 'towards': 'west'}, 'refused-unknown-command'),
        ({'kind': 'go', 'to': {'x': WEST + 1, 'y': NORTH}}, 'refused-unknown-command'),
        ({'kind': 'roam', 'to': {'x': 'alpha', 'y': NORTH}}, 'refused-unknown-command'),
        ({'kind': 'roam', 'to': {'x': True, 'y': NORTH}}, 'refused-unknown-command'),
        ({'kind': 'roam'}, 'refused-unknown-command'),
        ({'kind': 'roam', 'direction': 'up'}, 'refused-unknown-command'),
        ({'kind': 'roam', 'direction': 'n', 'to': {'x': WEST, 'y': NORTH}}, 'refused-unknown-command'),
        ({'kind': 'camp', 'direction': 'n'}, 'refused-unknown-command'),
        ({'kind': 'roam', 'to': {'x': WEST - 1, 'y': NORTH}}, 'refused-no-such-place'),
        (council.going('roam', HOME), 'refused-no-such-place'),
        (council.going('roam', (WEST + 5, NORTH + 1)), 'refused-no-such-place'),
        (council.going('explore', (WEST + 1, NORTH + 1)), 'refused-no-such-place'),
        (council.heading('explore', 'e'), 'refused-no-such-place'),
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
        ('council-followed', {'proposal': 'proposal-camp'}),
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
    band(game).stores = Stock()
    for member in band(game).members[1:4]:
        member.thirsty = 1.5
    game.answered = {'today': answered, 'tomorrow': None}

    lost = said(steps(game, 2))

    blamed = [('seat-blamed', {'lost': 3, 'status': status})] if answered else []
    assert lost[lost.index(('people-lost', {'count': 3, 'cause': 'thirst'})) + 1 :] == blamed
    assert game.status == status


def test_deaths_the_council_is_not_blamed_for_cost_nothing_and_call_no_council(params: Params) -> None:
    game = land(params)
    game.answered = {'today': 'voted', 'tomorrow': None}
    tick = _Tick()

    game._lost(tick, 'age', 2)

    assert [(event.key, event.values) for event in tick.events] == [('people-lost', {'count': 2, 'cause': 'age'})]
    assert (game.status, game.since[council.DEATH]) == (50.0, 0)


@pytest.mark.parametrize(('answered', 'status'), [('voted', 55.0), ('silent', 50.0), (None, 50.0)])
def test_a_birth_earns_five_only_on_a_day_the_player_voted_for(answered: str | None, status: float) -> None:
    fed = {'units.band.consumption_per_day.forage': 0.0, 'units.band.consumption_per_day.water': 0.0}
    sure = {'units.band.people.birth.child_survives': 1.0, 'units.band.people.birth.mother_dies': 0.0}
    game = land(load_params(overrides={**SMALL, **fed, **sure}))
    band(game).members[0].pregnant_until = game.day
    game.answered = {'today': answered, 'tomorrow': None}

    born = [(key, values) for key, values in said(steps(game, 2)) if key.startswith(('people-', 'seat-'))]

    praised = [('seat-praised', {'born': 1, 'status': status})] if answered == 'voted' else []
    assert born == [('people-born', {'count': 1}), *praised]
    assert game.answered == {'today': None, 'tomorrow': None}


def test_an_intent_to_stay_never_moves(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=SUMMER + 1)
    bind(game, STAY)

    kinds = {result.units[0][4] for result in steps(game, DAY - 1)}

    assert kinds <= {'gather', 'camp'}


WALL = (('grass', 'water', 'grass'), ('grass', 'water', 'grass'), ('grass', 'grass', 'grass'))
SHUT = (('grass', 'water', 'grass'), ('water', 'water', 'grass'), ('grass', 'grass', 'grass'))
ACROSS = council.going('roam', (WEST + 2, NORTH))


def test_a_go_walks_its_route_round_the_water(params: Params) -> None:
    game = land(params, at=(WEST, NORTH), rows=WALL, parts=SUMMER)
    bind(game, ACROSS)

    game.step()
    route = band(game).route

    assert route is not None
    assert route['cells'] == [[WEST, NORTH + 1], [WEST + 1, NORTH + 2], [WEST + 2, NORTH + 1], [WEST + 2, NORTH]]
    assert band(game).action == {'kind': 'roam', 'towards': 'south'}


def test_a_go_with_no_way_is_refused_and_one_held_ends_and_calls_the_council(params: Params) -> None:
    game = land(params, at=(WEST, NORTH), rows=SHUT, parts=SUMMER)
    sit(game, (STAY, 14))
    refused = vote(game, ACROSS)
    bind(game, ACROSS)

    ended = game.step()

    assert told(refused)[0] == ('command-refused', {'id': 'c-1', 'reason': 'refused-no-such-place'})
    assert told(ended) == [('plan-ended', {'proposal': 'proposal-roam-e', 'why': 'closed'})]
    assert (band(game).intent, game.since['spent']) == (None, True)


def test_a_band_that_reaches_its_target_calls_the_council_that_evening(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=SUMMER + 1)
    quiet(game)
    bind(game, council.going('roam', (WEST + 1, NORTH + 1)))

    afternoon, evening = steps(game, 2)

    assert band(game).place == (WEST + 1, NORTH + 1)
    assert told(afternoon) == []
    assert told(evening)[0] == ('plan-ended', {'proposal': 'proposal-roam', 'why': 'reached'})
    assert told(evening)[-1][1]['occasion'] == 'occasion-spent'


def test_a_plan_with_a_way_aims_at_its_next_leg_and_is_spent_when_nothing_better_lies_that_way(
    params: Params,
) -> None:
    game = land(params, stripped=STRIPPED, parts=SUMMER + 1)
    bind(game, council.heading('roam', 'e'))
    first = band(game).intent
    assert first is not None and first['leg'] is not None
    band(game).x, band(game).y = first['leg']['x'], first['leg']['y']
    tick = _Tick()

    game._leg(tick, band(game))

    ahead = band(game).intent
    if ahead is None:
        assert [(event.key, event.values['why']) for event in tick.events] == [('plan-ended', 'nothing')]
    else:
        assert ahead['leg'] != first['leg'] and tick.events == []
        assert council.sector(band(game).place, (ahead['leg']['x'], ahead['leg']['y'])) == 'e'


@pytest.mark.parametrize('winter', [False, True])
@pytest.mark.parametrize('proposal', [EAST, STAY])
def test_a_tired_band_rests_whatever_it_is_bound_to(params: Params, proposal: dict[str, Any], winter: bool) -> None:
    game = land(params, stripped=STRIPPED, parts=SUMMER + 1)
    bind(game, proposal)
    if winter and proposal == STAY:
        wintering(game)
    band(game).states = ['tiredness']

    game.step()

    assert band(game).action == {'kind': 'camp'}
    assert band(game).reason == {'action': 'camp', 'need': 'rest', 'score': 0.0, 'pull': None}


def test_a_point_the_others_did_not_name_is_weighed_by_them_and_wins_some(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    band(game).lore['known'] = ['orientation']
    game.status = 80.0
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))
    far = council.going('explore', (WEST + 5, NORTH + 1))

    turned = vote(game, far)

    key, values = told(turned)[-1]
    assert (key, values['proposal'], values['all']) == ('council-turned', 'proposal-explore-e', 20.0)
    assert values['yes'] >= 6.0
    assert intent(game)['proposal'] == far


@pytest.mark.parametrize(
    ('proposal', 'now', 'verdict'),
    [
        (EAST, 0.3, 'worked'),
        (EAST, 0.2, 'failed'),
        (EAST, 0.25, 'even'),
        (STAY, 0.28, 'even'),
        (STAY, 0.5, 'worked'),
        (STAY, 0.1, 'failed'),
    ],
)
def test_the_verdicts_of_the_document_judge_the_land_only(
    params: Params, proposal: dict[str, Any], now: float, verdict: str
) -> None:
    judgement = {'proposal': proposal, 'expected': 0.3, 'before': 0.35}

    assert council.verdict(params, judgement, now) == verdict


@pytest.mark.parametrize(
    ('proposal', 'verdict', 'amount'),
    [
        (EAST, 'worked', 4.0),
        (EAST, 'failed', -6.0),
        (EAST, 'even', 0.0),
        (STAY, 'worked', 3.0),
        (STAY, 'failed', -6.0),
        (STAY, 'even', 0.0),
        (council.heading('explore', 'n'), 'worked', 4.0),
        (council.heading('explore', 'n'), 'failed', -6.0),
        (council.heading('explore', 'n'), 'even', 0.0),
    ],
)
def test_what_moves_status(params: Params, proposal: dict[str, Any], verdict: str, amount: float) -> None:
    assert council.amount(params, proposal, verdict) == amount


def test_the_worth_of_the_land_is_weighed_by_the_needs_given(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    hungry = {'hunger': 1.0, 'thirst': 0.0}
    stripped = council.worth(params, band(game), 'band', hungry, 0.0)
    band(game).x = WEST + 3
    bands.look(game, band(game), game.day)

    assert council.worth(params, band(game), 'band', hungry, 0.0) > stripped
    assert council.worth(params, band(game), 'band', {'hunger': 0.0, 'thirst': 0.0}, 0.0) < 0


def test_a_death_under_a_judgement_is_paid_once_and_only_on_the_day_voted_for(params: Params) -> None:
    struck = load_params(
        overrides={
            **SMALL,
            'encounters.chance': 1.0,
            'encounters.kinds.predator.loss.min': 0.05,
            'encounters.kinds.predator.loss.max': 0.05,
            'biomes.forest.eras.band.properties.threat.base': 1.0,
            'units.band.shelter.encounter': 1.0,
        }
    )
    game = land(struck, at=(WEST + 3, NORTH + 1))
    sit(game, (EAST, 2), (STAY, 0))

    results = [vote(game, STAY), *steps(game, DAY - 1)]
    taken = sum(values['lost'] for key, values in said(results) if key == 'encounter')
    blamed = sum(values['lost'] for key, values in said(results) if key == 'seat-blamed')
    [(found, values)] = judged(results[-1])
    paid = {'proposal-worked': 3.0, 'proposal-even': 0.0, 'proposal-failed': -6.0}[found]

    assert said(results)[1][0] == 'council-turned'
    assert (taken, blamed) == (3, 2)
    assert values == {'proposal': 'proposal-camp', 'status': 50.0 - 5.0 * blamed + paid}


def test_status_rises_slowly_near_the_top_and_is_held_at_a_hundred(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    game.status = 99.0
    sit(game, (STAY, 8), (NORTHWARD, 1), (EAST, 5))

    results = [vote(game, EAST)]
    game.since['first'] = False
    results += steps(game, 3 * DAY)

    verdicts = [held for result in results for held in judged(result)]
    assert verdicts == [('proposal-worked', {'proposal': 'proposal-roam-e', 'status': 99.08})]
    assert council.held(105.0) == 100.0


@pytest.mark.parametrize(
    ('amount', 'status', 'paid'),
    [(4.0, 50.0, 4.0), (4.0, 90.0, 0.8), (-6.0, 90.0, -10.8), (4.0, 20.0, 4.0), (-2.0, 2.0, -2.0)],
)
def test_status_is_weighed_by_its_height_above_the_middle(amount: float, status: float, paid: float) -> None:
    assert council.scaled(amount, status) == pytest.approx(paid)


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
    assert snapshot['units'][0]['intent']['proposal'] == EAST
    assert copy.state_hash() == game.state_hash()
    assert [told(result) for result in steps(copy, 2)] == [told(result) for result in steps(game, 2)]
    assert copy.state_hash() == game.state_hash()
    assert copy.council == game.council is not None


def test_a_year_of_votes_gives_the_same_hashes_twice(params: Params) -> None:
    offsets = [(3, 0), (0, -2), None, (-2, 2)]

    def year(game: Game) -> tuple[list[str], float, int]:
        found = []
        for tick in range(params.time.parts_per_day * params.time.days_per_year):
            if game.council is not None and tick % 3:
                way = offsets[tick // 5 % len(offsets)]
                to = None if way is None else (band(game).x + way[0], band(game).y + way[1])
                kind = 'roam' if to in band(game).known else 'explore'
                said_here = STAY if to is None else council.going(kind, to)
                game.submit(Vote(seat='player', proposal=said_here))
            found.append(game.step().hash)
            if game.over:
                break
        return found, game.status, int(councils(game))

    first = year(Game.create(seed=7, params=params, seated=True))

    assert first == year(Game.create(seed=7, params=params, seated=True))
    assert first[2] > 0
    assert first[1] != params.council.status.start


@pytest.mark.parametrize(
    ('day', 'offered'),
    [(20, False), (49, False), (50, True), (70, True), (99, True), (100, False), (149, False), (150, True)],
)
def test_a_winter_camp_is_offered_in_the_autumn_and_the_winter(params: Params, day: int, offered: bool) -> None:
    assert council.offered(params, day) is offered


def test_a_camp_in_its_season_is_scored_as_the_winter_camp_under_less_threat(params: Params) -> None:
    game = land(params, parts=WINTER + 2)

    offered = council.score(params, band(game), ERA, game.inside, wintering=True)
    stand = council.score(params, band(game), ERA, game.inside)

    assert offered[0][0] == stand[0][0] == STAY
    assert offered[0][1] > stand[0][1]
    assert [proposal for proposal, _, _ in offered].count(STAY) == 1
    assert game.wintering
    assert council.key(STAY, band(game), winter=True) == 'proposal-winter-camp'
    assert council.key(STAY, band(game)) == 'proposal-camp'


def test_a_camp_is_taken_in_any_season_and_is_the_winter_camp_only_in_its_season(params: Params) -> None:
    summer, winter = land(params), land(params, parts=WINTER + 3)
    for game in (summer, winter):
        sit(game, (STAY, 14))

    taken = [vote(game, STAY) for game in (summer, winter)]

    assert [told(held)[0] for held in taken] == [('command-accepted', {'id': 'c-1'})] * 2
    assert (summer.camping, summer.wintering, winter.wintering) == (True, False, True)
    assert [intent(game)['winter'] for game in (summer, winter)] == [False, True]


def test_a_built_camp_is_worth_its_keep_and_less_threat_only_in_its_season(params: Params) -> None:
    game = land(params, parts=WINTER + 2)
    held = band(game)
    held.camp = {'x': held.x, 'y': held.y, 'built': 1.0}
    rules = params.units.band

    cold, warm = (
        council.score(params, held, ERA, game.inside, wintering=True, cold=flag)[0][1] for flag in (True, False)
    )
    held.season = 'winter'
    winter = (decisions.seen(params, held, held.place, ERA) or {})['threat']
    held.season = 'summer'
    summer = (decisions.seen(params, held, held.place, ERA) or {})['threat']

    assert cold - warm == pytest.approx(rules.decisions.weights.move * rules.winter_camp.kept)
    assert winter == pytest.approx(summer * rules.winter_camp.threat)


def test_a_band_bound_to_a_winter_camp_builds_it_for_two_days_and_then_stays(params: Params) -> None:
    game = land(params, parts=WINTER)
    quiet(game)
    bind(game, STAY)
    band(game).stores = Stock({'forage': [[float(game.day), 45.0]], 'water': [[float(game.day), 45.0]]})

    kinds = [result.units[0][4] for result in steps(game, 3 * DAY)]

    assert kinds[: 2 * DAY] == ['build'] * 3 + ['camp'] * 2 + ['build'] * 3 + ['camp'] * 2
    assert set(kinds[2 * DAY :]) <= {'gather', 'camp'}
    assert bands.sheltered(band(game))
    assert (intent(game)['proposal'], intent(game)['winter']) == (STAY, True)
    assert band(game).reason is not None


def test_the_winter_does_not_end_a_winter_camp_and_the_spring_calls_the_council(params: Params) -> None:
    wintered, sprung = land(params, parts=WINTER + 2), land(params, parts=SPRING + 2)
    for game in (wintered, sprung):
        quiet(game)
        wintering(game)
        game.since['season'] = True

    held, ended = wintered.step(), sprung.step()

    assert [key for key, _ in told(held) if key.startswith('council-')] == []
    assert told(ended)[-1][1]['occasion'] == 'occasion-season'


def test_the_term_of_a_winter_camp_ends_with_the_first_day_that_offers_none(params: Params) -> None:
    assert council.until(params, 75, True) == 100
    assert council.until(params, 20, False) == 20 + params.days(params.council.term)


def test_a_starving_band_bound_to_a_winter_camp_gathers_before_it_builds_and_a_hungry_one_builds(
    params: Params,
) -> None:
    starving, hungry = land(params, parts=WINTER), land(params, parts=WINTER)
    for game in (starving, hungry):
        quiet(game)
        wintering(game)
        band(game).stores = Stock()
    band(starving).states = ['starvation']

    starving.step()
    hungry.step()

    assert band(starving).action['kind'] in ('gather', 'camp')
    assert band(starving).camp is None
    assert band(hungry).action == {'kind': 'build'}


def test_the_others_judge_a_winter_camp_by_its_reach(params: Params) -> None:
    game = land(params, stripped=[HOME], parts=WINTER + 2)

    offered = council.score(params, band(game), ERA, game.inside, wintering=True)
    stand = council.score(params, band(game), ERA, game.inside)

    assert offered[0][1] > stand[0][1]


def test_a_hungry_band_bound_to_a_winter_camp_gathers_its_reach(params: Params) -> None:
    game = land(params, stripped=[HOME], parts=WINTER)
    quiet(game)
    wintering(game)
    band(game).stores = Stock({'water': [[float(game.day), 45.0]]})
    band(game).states = ['starvation']

    game.step()
    near = [at for at in bands.around(HOME, 1) if game.inside(*at)]

    assert band(game).action['kind'] == 'gather'
    assert max(band(game).action['shares'].items(), key=lambda held: held[1])[0] == 'forage'
    assert game.cells.stock(HOME, 'food') == pytest.approx(0.1, abs=0.01)
    assert any(game.cells.stock(at, 'food') < 1.0 for at in near)


@pytest.mark.parametrize('parts', [SPRING - 1, 70 * DAY - 1])
def test_a_winter_camp_stands_through_a_new_season_while_the_band_stays_on_it(params: Params, parts: int) -> None:
    game = land(params, parts=parts)
    camp = {'x': WEST, 'y': NORTH + 1, 'built': 1.0}
    band(game).camp = dict(camp)

    game.step()

    assert game.date.part == 'morning'
    assert band(game).camp == camp


def test_camping_in_a_built_camp_is_worth_kept_more_to_the_others() -> None:
    even = {'units.band.winter_camp.threat': 1.0, 'units.band.winter_camp.consumption': 1.0}
    params = load_params(overrides={**SMALL, **even})
    game = land(params, parts=WINTER + 2)
    camp = {'x': HOME[0], 'y': HOME[1], 'built': 0.5}
    band(game).camp = dict(camp)
    building = council.score(params, band(game), ERA, game.inside, wintering=True)
    band(game).camp = {**camp, 'built': 1.0}
    built = council.score(params, band(game), ERA, game.inside, wintering=True)

    assert [proposal for proposal, _, _ in built] == [proposal for proposal, _, _ in building]
    assert built[0][1] == pytest.approx(building[0][1] + 3.0 * 0.2)
    assert [held for _, held, _ in built[1:]] == pytest.approx([held for _, held, _ in building[1:]])


def test_a_place_no_option_names_is_refused_to_a_band_without_orientation(params: Params) -> None:
    lost, oriented, named = land(params), land(params), land(params)
    band(lost).lore['known'] = band(named).lore['known'] = []
    for game in (lost, oriented):
        sit(game, (STAY, 14))
    sit(named, (STAY, 10), (EAST, 4))

    refused, taken, backed = vote(lost, EAST), vote(oriented, EAST), vote(named, EAST)

    assert told(refused)[0] == ('command-refused', {'id': 'c-1', 'reason': 'refused-not-learned'})
    assert told(taken)[0] == ('command-accepted', {'id': 'c-1'})
    assert told(backed)[0] == ('command-accepted', {'id': 'c-1'})


def test_a_band_that_never_wintered_camps_as_a_stand_in_the_winter(params: Params) -> None:
    game = land(params, parts=WINTER + 3)
    band(game).lore['known'] = []
    sit(game, (STAY, 14))

    offered = game.wintering
    taken = vote(game, STAY)
    laid = council.table(params, band(game), ERA, game.inside, (), game.wintering)

    assert not offered
    assert told(taken)[0] == ('command-accepted', {'id': 'c-1'})
    assert intent(game)['winter'] is False
    assert 'proposal-winter-camp' not in [entry['key'] for entry in laid]


def test_the_council_says_whether_the_player_may_name_a_place_of_their_own(params: Params) -> None:
    lost, oriented = land(params, stripped=STRIPPED, parts=AFTERNOON), land(params, stripped=STRIPPED, parts=AFTERNOON)
    band(lost).lore['known'] = []

    for game in (lost, oriented):
        game.step()

    assert lost.council is not None and oriented.council is not None
    assert (lost.council['place'], oriented.council['place']) == (False, True)
    assert set(oriented.council['stores']) == {'food', 'water'}


def test_a_built_camp_whose_reach_is_stripped_is_worth_no_more_than_its_land() -> None:
    even = {'units.band.winter_camp.threat': 1.0, 'units.band.winter_camp.consumption': 1.0}
    params = load_params(overrides={**SMALL, **even})
    game = land(params, stripped=STRIPPED, parts=WINTER + 2)
    camp = {'x': HOME[0], 'y': HOME[1], 'built': 0.5}
    band(game).camp = dict(camp)
    building = council.score(params, band(game), ERA, game.inside, wintering=True)
    band(game).camp = {**camp, 'built': 1.0}
    built = council.score(params, band(game), ERA, game.inside, wintering=True)

    assert decisions.stripped(params, band(game), ERA)
    assert [held for _, held, _ in built] == pytest.approx([held for _, held, _ in building])


def starving(game: Game) -> bands.Band:
    held = band(game)
    held.stores = Stock()
    held.restocked()
    held.states.append(bands.STARVATION)
    return held


def test_a_band_short_of_food_on_stripped_land_keeps_only_the_best_land_nearest(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    held = starving(game)

    days = council.score(params, held, ERA, game.inside)
    found = council.survived(params, held, ERA, days)

    assert any(proposal == STAY for proposal, _, _ in days)
    assert found and all(proposal['kind'] == 'roam' for proposal, _, _ in found)
    assert {at[0] for _, _, at in found} == {WEST + 2}


def test_a_starving_band_on_the_best_land_it_knows_stays_to_gather(params: Params) -> None:
    around = [(x, y) for x in range(WEST, WEST + 6) for y in range(NORTH, NORTH + 3) if (x, y) != HOME]
    game = land(params, stripped=around)
    held = starving(game)
    days = council.score(params, held, ERA, game.inside)

    assert council.survived(params, held, ERA, days) == days


def camped(game: Game, stores: dict[str, float]) -> bands.Band:
    held = band(game)
    held.camp = {'x': held.x, 'y': held.y, 'built': 1.0}
    held.stores = Stock({name: [[float(game.day), amount]] for name, amount in stores.items()})
    held.restocked()
    return held


@pytest.mark.parametrize(('parts', 'kept'), [(WINTER + 2, True), (EVENING, False)])
def test_a_band_whose_stocked_camp_it_could_not_carry_away_has_no_way_off_only_in_the_seasons_of_the_camp(
    params: Params, parts: int, kept: bool
) -> None:
    game = land(params, stripped=STRIPPED, parts=parts)
    held = camped(game, {'dried': 2000.0, 'water': 45.0})
    days = council.score(params, held, ERA, game.inside, (EAST,))

    found = council.survived(params, held, ERA, days)

    assert council.stocked(params, held) == kept
    assert any(proposal['kind'] == 'roam' for proposal, _, _ in days)
    assert found == ([day for day in days if day[0]['kind'] == 'camp'] if kept else days)


def test_a_camp_is_not_kept_for_spare_goods_or_water_on_unsafe_land_or_by_a_starving_band(params: Params) -> None:
    unsafe = load_params(overrides={**SMALL, 'units.band.winter_camp.unsafe': 0.0})
    spare = camped(land(params, parts=WINTER + 2), {'sticks': 4000.0, 'water': 45.0})
    watered = camped(land(params, parts=WINTER + 2), {'forage': 20.0, 'water': 4000.0})
    dangerous = camped(land(unsafe, parts=WINTER + 2), {'dried': 2000.0, 'water': 45.0})
    game = land(params, stripped=STRIPPED, parts=WINTER + 2)
    hungry = camped(game, {'dried': 2000.0, 'water': 45.0})
    hungry.states.append(bands.STARVATION)
    days = council.score(params, hungry, ERA, game.inside, (EAST,))

    assert (council.stocked(params, spare), council.stocked(params, watered)) == (False, False)
    assert not council.stocked(unsafe, dangerous)
    assert council.stocked(params, hungry)
    assert any(proposal['kind'] == 'roam' for proposal, _, _ in council.survived(params, hungry, ERA, days))


def test_a_band_that_hunger_presses_fears_nothing(params: Params) -> None:
    held = band(land(params))
    cell = {'food': 0.5, 'water': 0.5, 'threat': 0.9}
    safe = {**cell, 'threat': 0.0}
    hungry, fed = {'hunger': 0.8, 'thirst': 0.1}, {'hunger': 0.1, 'thirst': 0.1}

    def worth(wanted: dict[str, float], land: dict[str, float]) -> float:
        return decisions.worth(params, held, land, wanted, goods=False)[0]

    assert worth(hungry, cell) == worth(hungry, safe)
    assert worth(fed, cell) < worth(fed, safe)


def test_a_band_remembers_the_camps_it_built_and_puts_an_old_one_in_order_in_an_evening(params: Params) -> None:
    game = land(params, parts=WINTER + 2)
    held = band(game)
    held.camp = {'x': held.x, 'y': held.y, 'built': 0.9}
    quiet(game)
    wintering(game)
    game.step()
    built = list(held.camps)
    held.camp = None
    quiet(game)
    wintering(game)

    game.step()

    assert built == [HOME]
    assert held.camp == {'x': HOME[0], 'y': HOME[1], 'built': 1.0}


def test_a_band_short_of_food_in_a_winter_camp_leaves_beyond_its_reach(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=WINTER + 2)
    held = starving(game)
    held.camp = {'x': held.x, 'y': held.y, 'built': 1.0}
    wintering(game)
    days = council.score(params, held, ERA, game.inside, wintering=True)

    found = council.survived(params, held, ERA, days)

    reach = params.units.band.winter_camp.reach
    assert found and all(decisions.far(held.place, at) > reach for _, _, at in found)


def test_a_band_short_of_food_keeps_every_option_until_its_stores_run_out(params: Params) -> None:
    game = land(params, stripped=STRIPPED)
    held = band(game)
    held.stores = Stock()
    held.restocked()
    days = council.score(params, held, ERA, game.inside)

    assert council.survived(params, held, ERA, days) == days


def test_a_starving_band_bound_to_a_roam_walks_and_does_not_stop_to_gather(params: Params) -> None:
    game = land(params, stripped=STRIPPED, parts=AFTERNOON)
    starving(game)
    bind(game, EAST)

    game.step()

    assert band(game).action['kind'] in ('move', 'roam')


def test_a_fed_band_keeps_every_option(params: Params) -> None:
    game = land(params)
    days = council.score(params, band(game), ERA, game.inside)

    assert council.survived(params, band(game), ERA, days) == days


def test_a_camp_on_land_too_dangerous_for_a_winter_camp_is_the_stand(params: Params) -> None:
    game = land(params, parts=WINTER + 3)
    safe = council.winters(params, band(game), game.wintering)
    band(game).dread[band(game).place] = 0.8
    sit(game, (STAY, 14))

    taken = vote(game, STAY)

    assert safe and not council.winters(params, band(game), game.wintering)
    assert told(taken)[0] == ('command-accepted', {'id': 'c-1'})
    assert intent(game)['winter'] is False


@pytest.mark.parametrize(
    ('fields', 'proposal'),
    [
        ({'proposal': {'kind': 'camp'}}, {'kind': 'camp'}),
        ({'proposal': {'kind': 'roam', 'direction': 'ne'}}, {'kind': 'roam', 'direction': 'ne'}),
        ({'proposal': {'kind': 'explore', 'to': {'x': 1, 'y': 2}}}, {'kind': 'explore', 'to': {'x': 1, 'y': 2}}),
        ({'proposal': {'kind': 'abstain'}}, {'kind': 'abstain'}),
        ({'proposal': {'kind': 'explore'}}, None),
        ({'proposal': {'kind': 'roam', 'direction': 'north'}}, None),
        ({'proposal': {'kind': 'go', 'to': {'x': 1, 'y': 2}}}, None),
        ({'proposal': {'kind': 'stay-and-gather'}}, None),
    ],
)
def test_a_proposal_is_a_camp_or_a_roam_or_an_explore_with_a_way_or_a_cell(
    fields: dict[str, Any], proposal: dict[str, Any] | None
) -> None:
    assert council.answer(fields) == proposal


@pytest.mark.parametrize(
    ('to', 'way'),
    [((0, -3), 'n'), ((2, -2), 'ne'), ((3, 0), 'e'), ((3, 1), 'e'), ((1, 3), 's'), ((-2, 2), 'sw'), ((-3, -1), 'w')],
)
def test_a_cell_lies_in_one_of_eight_ways_of_45_degrees(to: tuple[int, int], way: str) -> None:
    assert council.sector((10, 10), (10 + to[0], 10 + to[1])) == way


def test_a_plan_is_told_by_its_way_or_the_way_of_its_cell(params: Params) -> None:
    held = band(land(params))

    assert council.key(council.heading('explore', 'sw')) == 'proposal-explore-sw'
    assert council.key(EAST, held) == 'proposal-roam-e'
    assert council.key(council.going('roam', HOME), held) == 'proposal-roam'
    assert council.key(EAST) == 'proposal-roam'


def test_two_plans_aimed_at_the_same_cell_are_one_option(params: Params) -> None:
    game = land(params, stripped=STRIPPED)

    days = council.score(params, band(game), ERA, game.inside, (EAST,))
    ways = [at for proposal, _, at in days if 'direction' in proposal or proposal == STAY]

    assert len(ways) == len(set(ways))
    assert any(proposal == EAST for proposal, _, _ in days)


RHYTHM = {**SMALL, 'units.band.plan.march': 3.0, 'units.band.plan.stock': 5.0, 'units.band.carry_kg': 30.0}
LURING = {**SMALL, 'units.band.decisions.horizon': 2, 'units.band.decisions.distance_known': 0.5}
NO_POOR = {'units.band.decisions.lure.poor': 0.0}
NO_LURE = {**NO_POOR, 'units.band.decisions.lure.crowded': 0.0}
WIDE = (('grass',) * 12,) * 7
MIDDLE = (WEST + 6, NORTH + 3)
EVERY = [(x, y) for x in range(WEST, WEST + 12) for y in range(NORTH, NORTH + 7)]


def supplied(game: Game, food: float, water: float) -> bands.Band:
    """
    The stores of the band, in days of forage and of water.
    """
    held = band(game)
    eaters = bands.census(game.params, held).eaters
    day = float(game.day)
    held.stores = Stock({'forage': [[day, food * eaters]], 'water': [[day, water * eaters]]})
    held.restocked()
    return held


def standing(game: Game, stood: bool) -> None:
    band(game).intent = {**intent(game), 'standing': stood}


@pytest.mark.parametrize(
    ('food', 'water', 'stood', 'stands'),
    [
        (4.0, 4.0, False, False),
        (3.0, 3.0, False, False),
        (2.0, 4.0, False, True),
        (4.0, 2.0, False, True),
        (4.0, 4.0, True, True),
        (5.0, 4.0, True, True),
        (5.0, 5.0, True, False),
    ],
)
def test_a_band_on_a_leg_marches_on_its_stores_and_a_stand_stocks_them(
    food: float, water: float, stood: bool, stands: bool
) -> None:
    game = land(load_params(overrides=RHYTHM))
    bind(game, EAST)
    supplied(game, food, water)
    standing(game, stood)

    assert council.stands(game.params, band(game), ERA) is stands


def test_a_tired_band_stands_and_a_starving_or_thirsting_one_never_does() -> None:
    game = land(load_params(overrides=RHYTHM))
    bind(game, EAST)
    supplied(game, 9.0, 9.0)
    band(game).states = ['tiredness']
    assert council.stands(game.params, band(game), ERA)

    supplied(game, 0.0, 9.0)
    standing(game, True)
    band(game).states = ['starvation']
    assert not council.stands(game.params, band(game), ERA)

    supplied(game, 9.0, 0.0)
    band(game).states = ['thirst']
    assert not council.stands(game.params, band(game), ERA)


@pytest.mark.parametrize('stood', [False, True])
def test_a_band_does_not_stand_on_land_that_gives_no_days_food(stood: bool) -> None:
    game = land(load_params(overrides=RHYTHM), stripped=STRIPPED)
    bind(game, EAST)
    supplied(game, 1.0, 1.0)
    standing(game, stood)

    assert decisions.barren(game.params, band(game), ERA)
    assert not council.stands(game.params, band(game), ERA)


@pytest.mark.parametrize('stood', [False, True])
def test_a_band_that_could_carry_no_more_does_not_stand_for_its_stores(stood: bool) -> None:
    game = land(load_params(overrides={**RHYTHM, 'units.band.carry_kg': 6.0}))
    bind(game, EAST)
    supplied(game, 2.0, 4.0)
    standing(game, stood)

    assert not council.stands(game.params, band(game), ERA)


def test_a_band_finishes_its_step_before_it_stands_and_only_tiredness_stops_it() -> None:
    game = land(load_params(overrides=RHYTHM), parts=SUMMER)
    bind(game, EAST)
    supplied(game, 2.0, 4.0)
    band(game).progress, band(game).target = 0.5, (WEST + 1, NORTH + 1)

    band(game).states = ['tiredness']
    assert council.stands(game.params, band(game), ERA)
    band(game).states = []
    assert not council.stands(game.params, band(game), ERA)

    game.step()

    assert band(game).action['kind'] in ('move', 'roam')
    assert band(game).place == (WEST + 1, NORTH + 1) and band(game).progress == 0.0
    assert council.stands(game.params, band(game), ERA)


def test_a_stocked_band_walks_its_leg() -> None:
    game = land(load_params(overrides=RHYTHM), parts=SUMMER)
    bind(game, EAST)
    supplied(game, 4.0, 4.0)

    game.step()

    assert band(game).action['kind'] in ('move', 'roam')
    assert not intent(game)['standing']


def test_a_band_short_of_its_march_stands_gathers_and_stays_on_its_cell() -> None:
    game = land(load_params(overrides=RHYTHM), parts=SUMMER)
    bind(game, EAST)
    supplied(game, 2.0, 4.0)

    game.step()

    assert band(game).action['kind'] in ('gather', 'camp')
    assert band(game).place == HOME
    assert intent(game)['standing']


def test_a_starving_band_on_a_leg_walks_on() -> None:
    game = land(load_params(overrides=RHYTHM), stripped=STRIPPED, parts=AFTERNOON)
    bind(game, EAST)
    starving(game)

    game.step()

    assert band(game).action['kind'] in ('move', 'roam')
    assert not intent(game)['standing']


def test_the_end_of_a_stand_picks_the_next_leg() -> None:
    game = land(load_params(overrides=RHYTHM), stripped=STRIPPED, parts=SUMMER)
    way = council.heading('roam', 'e')
    bind(game, way)
    expected = council.aim(game.params, band(game), ERA, game.inside, way)
    assert expected is not None
    band(game).intent = {**intent(game), 'standing': True, 'leg': {'x': WEST + 1, 'y': NORTH}}

    game._rhythm(_Tick(), band(game))

    assert not intent(game)['standing']
    assert intent(game)['leg'] == {'x': expected[0], 'y': expected[1]}


def test_the_end_of_a_stand_with_nothing_left_that_way_spends_the_plan() -> None:
    game = land(load_params(overrides=RHYTHM), parts=SUMMER)
    bind(game, council.heading('roam', 'w'))
    supplied(game, 5.0, 5.0)
    standing(game, True)
    tick = _Tick()

    game._rhythm(tick, band(game))

    assert [(event.key, event.values['why']) for event in tick.events] == [('plan-ended', 'nothing')]
    assert (band(game).intent, game.since['spent']) == (None, True)


def test_a_stand_calls_no_council() -> None:
    game = land(load_params(overrides={**RHYTHM, 'units.band.plan.stock': 50.0}), parts=SUMMER)
    bind(game, EAST)
    supplied(game, 2.0, 4.0)
    game.since = dict(QUIET)

    results = steps(game, DAY)

    assert intent(game)['standing'] and band(game).place == HOME
    assert councils(game) == 0
    assert [key for key, _ in said(results) if key.startswith('council-')] == []


def test_a_council_that_keeps_the_plan_keeps_the_stand_and_another_plan_ends_it() -> None:
    game = land(load_params(overrides=RHYTHM))
    bind(game, EAST)
    standing(game, True)

    bind(game, EAST)
    assert intent(game)['standing']

    bind(game, STAY)
    assert not intent(game)['standing']


def test_a_camp_has_no_rhythm() -> None:
    game = land(load_params(overrides=RHYTHM), parts=SUMMER)
    bind(game, STAY)
    supplied(game, 1.0, 1.0)

    game._rhythm(_Tick(), band(game))

    assert not intent(game)['standing']


def test_rich_roomy_land_does_not_lure(params: Params) -> None:
    game = land(params)
    supplied(game, 0.5, 5.0)

    assert council.lure(params, band(game), ERA) == pytest.approx(1.0)


def test_a_band_that_hopes_for_nothing_of_the_unknown_is_not_lured_by_poor_land(params: Params) -> None:
    game = land(params, rows=WIDE, at=MIDDLE, stripped=EVERY)
    supplied(game, 5.0, 5.0)

    assert council.lure(params, band(game), ERA) == pytest.approx(1.0)


def test_poor_land_raises_the_lure() -> None:
    lured = load_params(overrides=LURING)
    game = land(lured, rows=WIDE, at=MIDDLE, stripped=EVERY)
    supplied(game, 0.5, 5.0)

    assert 1.5 < council.lure(lured, band(game), ERA) < 2.0


def test_a_band_eating_over_what_its_land_grows_is_lured() -> None:
    lured = load_params(overrides={**LURING, **NO_POOR})
    game = land(lured)
    band(game).members = bands.adults(100)
    band(game).changed()
    fed = decisions.feeding(lured, band(game), ERA)

    assert 100 / fed > lured.units.band.decisions.lure.from_
    assert council.lure(lured, band(game), ERA) == pytest.approx(1.0 + 100 / fed - 0.7)


def test_both_weights_at_zero_turn_the_lure_off() -> None:
    off = load_params(overrides={**LURING, **NO_LURE})
    game = land(off, rows=WIDE, at=MIDDLE, stripped=EVERY)
    band(game).members = bands.adults(200)
    band(game).changed()
    supplied(game, 0.5, 5.0)

    assert council.lure(off, band(game), ERA) == 1.0


def test_the_choice_of_a_band_in_a_tick_is_not_lured() -> None:
    lured, off = load_params(overrides=LURING), load_params(overrides={**LURING, **NO_LURE})
    game = land(lured, rows=WIDE, at=MIDDLE, stripped=EVERY)
    supplied(game, 0.5, 5.0)

    drawn = [(held.action, held.score) for held in decisions.options(lured, band(game), ERA)]
    plain = [(held.action, held.score) for held in decisions.options(off, band(game), ERA)]

    assert council.lure(lured, band(game), ERA) > 1.0
    assert drawn == plain


def explores(params: Params, game: Game) -> list[float]:
    days = council.score(params, band(game), ERA, game.inside)
    return [held for proposal, held, _ in days if proposal['kind'] == 'explore']


def test_explore_leads_the_table_of_a_hungry_band_on_poor_grazed_land_by_its_lure() -> None:
    lured, off = load_params(overrides=LURING), load_params(overrides={**LURING, **NO_LURE})
    game = land(lured, rows=WIDE, at=MIDDLE, stripped=EVERY)
    supplied(game, 0.5, 5.0)
    drawn = council.lure(lured, band(game), ERA)

    leader = council.leader(council.table(lured, band(game), ERA, game.inside))

    assert leader is not None and leader['kind'] == 'explore'
    assert explores(off, game)
    assert explores(lured, game) == pytest.approx([held * drawn for held in explores(off, game)])


def test_the_lure_does_not_make_an_explore_worth_nothing_any_worse() -> None:
    lured, off = load_params(overrides=LURING), load_params(overrides={**LURING, **NO_LURE})
    game = land(lured, rows=WIDE, at=MIDDLE)
    band(game).members = bands.adults(100)
    band(game).changed()
    supplied(game, 5.0, 5.0)

    assert council.lure(lured, band(game), ERA) > 1.0
    assert explores(lured, game) and all(held < 0 for held in explores(lured, game))
    assert explores(lured, game) == explores(off, game)
