import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.planet import Planet, place
from dominion_theory.planet.window import choose, misses, tries

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}


class Scripted:
    """
    A judge that answers from a list, one try after another, and remembers what it was asked.
    """

    def __init__(self, missed: list[int]) -> None:
        self.missed = missed
        self.asked: list[tuple[int, int]] = []

    def __call__(self, x: int, y: int) -> int:
        self.asked.append((x, y))
        return self.missed[len(self.asked) - 1]


def test_given_place_is_returned_as_it_is() -> None:
    given = load_params(overrides={**SMALL, 'planet.window.x': 5, 'planet.window.y': 7})
    judge = Scripted([])

    assert place(3, given) == (5, 7)
    assert choose(3, given, judge) == (5, 7)
    assert judge.asked == []


def test_placed_window_is_the_same_for_the_same_seed(params: Params) -> None:
    assert place(5, params) == place(5, params)
    assert tries(5, params) == tries(5, params)
    assert tries(5, params) != tries(6, params)


def test_every_try_lies_in_the_latitude_band_and_clear_of_the_seam(params: Params) -> None:
    window = params.planet.window
    places = tries(5, params)

    assert len(places) == window.tries
    assert place(5, params) in places
    for x, y in places:
        latitude = 1.0 - (y + window.height / 2) / 100
        assert 0 <= x <= 400 - window.width
        assert window.latitude.min - 0.01 <= latitude <= window.latitude.max + 0.01


def test_first_try_that_meets_every_need_is_taken(params: Params) -> None:
    judge = Scripted([2, 0, 0, 1])

    assert choose(5, params, judge) == tries(5, params)[1]
    assert judge.asked == tries(5, params)[:2]


def test_with_needs_that_cannot_be_met_the_best_try_is_taken(params: Params) -> None:
    few = load_params(overrides={**SMALL, 'planet.window.tries': 5})
    judge = Scripted([3, 1, 2, 1, 4])

    assert choose(5, few, judge) == tries(5, few)[1]
    assert judge.asked == tries(5, few)


def test_window_with_no_needs_misses_none_and_takes_the_first_try() -> None:
    none = {'land': 0.0, 'rivers': 0, 'biomes': {}}
    easy = load_params(overrides={**SMALL, 'planet.window.needs': none})
    planet = Planet(5, easy)
    x, y = tries(5, easy)[0]

    assert misses(planet.skeleton, planet.rivers, easy, x, y) == 0
    assert place(5, easy) == (x, y)


@pytest.mark.parametrize(
    ('needs', 'missed'),
    [
        ({'land': 0.0, 'rivers': 100000, 'biomes': {}}, 1),
        ({'land': 0.0, 'rivers': 100000, 'biomes': {'mountain': 1.0, 'tundra': 1.0}}, 3),
    ],
)
def test_every_need_that_is_not_met_is_counted(needs: dict[str, object], missed: int) -> None:
    hard = load_params(overrides={**SMALL, 'planet.window.needs': needs})
    planet = Planet(5, hard)
    x, y = tries(5, hard)[0]

    assert misses(planet.skeleton, planet.rivers, hard, x, y) == missed
    assert place(5, hard) in tries(5, hard)
