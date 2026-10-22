from typing import Any

import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, Observation, Option, Vote
from dominion_theory.engine.observation import Ground
from dominion_theory.players import SILENCE, Greedy, Leader, Minded, Random, Silent, made, sit, vote

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
# A voice that outweighs the band, so that the council sits and is never settled; no skill gates it.
LOUD = {**SMALL, 'council.voice.least': 20.0, 'skills': {}, 'encounters.chance': 0.0}
WITHIN = 200
GRASS = Ground('grass', 0.6, 0.4, 0.2, 1.0, False, False, 0)
FOREST = Ground('forest', 0.8, 0.5, 0.4, 0.5, True, False, 4)
STAY = Option(1, {'kind': 'stay-and-gather'}, 'proposal-stay-and-gather', 8, True, 0.5, GRASS)
EAST = Option(2, {'kind': 'go', 'to': {'x': 3, 'y': 0}}, 'proposal-go-forest', 6, False, 0.6, FOREST)
ABSTAINING = Option(3, {'kind': 'abstain'}, 'proposal-abstain', 0, False, 0.0, None)


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def seen(*options: Option) -> Observation:
    given: dict[str, Any] = {
        'year': 1,
        'month': 4,
        'day': 1,
        'part': 'evening',
        'season': 'summer',
        'people': {'child': 0, 'adult': 15, 'elder': 0},
        'pregnant': 0,
        'injured': 0,
        'sick': 0,
        'states': (),
        'fatigue': 0.0,
        'food_days': 2.0,
        'water_days': 2.0,
        'hunger': 0.0,
        'thirst': 0.0,
        'skills': (),
        'goods': {},
        'kits': {},
        'status': 50.0,
        'voice': 3.0,
        'occasion': 'first',
        'sight': 2,
        'winter_left': 1.0,
        'options': options or (STAY, EAST, ABSTAINING),
    }
    return Observation(**given)


def test_the_scripted_players_back_the_leader_say_nothing_or_back_the_best_score() -> None:
    assert Leader().answer(seen()) == 1
    assert Leader().answer(seen(EAST, ABSTAINING)) == SILENCE
    assert Silent().answer(seen()) == SILENCE
    assert Greedy().answer(seen()) == 2
    assert Greedy().answer(seen(ABSTAINING)) == SILENCE


def test_the_random_player_draws_from_its_seed_and_draw_with_silence_among_the_answers() -> None:
    drawn = [Random.drawn(7, 0).answer(seen()) for _ in range(3)]
    many = Random.drawn(7, 0)
    answers = {many.answer(seen()) for _ in range(200)}
    other = Random.drawn(7, 1)

    assert len(set(drawn)) == 1
    assert answers == {0, 1, 2, 3}
    assert [other.answer(seen()) for _ in range(20)] != [Random.drawn(7, 0).answer(seen()) for _ in range(20)]


def test_a_player_is_made_by_its_name_or_by_a_mind_of_the_tree(params: Params) -> None:
    minded = made({'mind': 'linear_v0'}, params, 7)

    assert isinstance(made('leader', params, 7), Leader)
    assert isinstance(made('random', params, 7, 2), Random)
    assert isinstance(minded, Minded) and minded.mind == params.minds['linear_v0']
    assert minded.answer(seen()) == 2
    with pytest.raises(ValueError, match='or a mind'):
        made('alpha', params, 7)
    with pytest.raises(ValueError, match='a mind of linear_v0'):
        made({'mind': 'beta'}, params, 7)


def test_an_answer_is_the_vote_of_its_option_and_one_naming_none_is_silence() -> None:
    assert vote(seen(), 2) == Vote('player', {'kind': 'go', 'to': {'x': 3, 'y': 0}})
    assert vote(seen(), 3) == Vote('player', {'kind': 'abstain'})
    assert vote(seen(), 0) is None
    assert vote(seen(), 9) is None


def test_a_player_in_the_seat_answers_the_council_and_its_vote_is_judged() -> None:
    game = Game.create(seed=7, params=load_params(overrides=LOUD), seated=True)

    asked = sit(game, Leader())
    for _ in range(WITHIN):
        if game.council is not None:
            break
        game.step()
    answered = sit(game, Leader())
    judged = game.step()

    assert asked is None
    assert answered is not None and answered[0] >= 1 and answered[1] is not None
    assert [event.key for event in judged.events if event.key.startswith('command-')] == ['command-accepted']
