import pytest

from dominion_theory.content import Params, load_params


@pytest.fixture
def params() -> Params:
    return load_params(overrides={'planet.window.width': 32, 'planet.window.height': 16})
