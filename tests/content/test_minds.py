from typing import Any

import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.core.errors import DominionError

PATH = 'minds.linear_v0'


def refused(mind: dict[str, Any]) -> dict[str, object]:
    with pytest.raises(DominionError) as raised:
        load_params(overrides={PATH: mind})

    assert raised.value.key == 'error-params-invalid'
    return raised.value.values


def test_the_first_mind_is_set_by_hand_to_back_the_band_and_never_abstain() -> None:
    minds = load_params().minds

    assert list(minds) == ['linear_v0']
    assert dict(zip(minds['linear_v0'].features, minds['linear_v0'].weights, strict=True)) == {
        'score': 1.0,
        'leader': 0.05,
        'abstain': -10.0,
    }
    assert minds['linear_v0'].trained == {'by': 'hand'}


@pytest.mark.parametrize(
    'mind',
    [
        {'features': ['alpha'], 'weights': [1.0]},
        {'features': ['score', 'score'], 'weights': [1.0, 1.0]},
        {'features': ['score'], 'weights': [1.0, 2.0]},
        {'features': [], 'weights': []},
    ],
)
def test_a_mind_weighs_known_features_once_each_with_a_weight_for_every_one(mind: dict[str, Any]) -> None:
    assert str(refused(mind)['path']).startswith(PATH)


def test_a_tree_written_before_the_minds_reads_with_none() -> None:
    tree = load_params().tree()
    del tree['minds']

    assert Params.model_validate(tree).minds == {}
