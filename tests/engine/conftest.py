import pytest

from dominion_theory.content import Params, load_params

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)
