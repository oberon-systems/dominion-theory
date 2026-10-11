import pytest
from pydantic import ValidationError

from dominion_theory.content import Duration


@pytest.mark.parametrize('unit', ['parts', 'days', 'months', 'years'])
def test_duration_names_one_unit(unit: str) -> None:
    duration = Duration.model_validate({unit: 3})

    assert (duration.unit, duration.amount) == (unit, 3)
    assert duration.model_dump() == {unit: 3}


@pytest.mark.parametrize(
    'written',
    [
        {},
        {'days': 1, 'months': 1},
        {'weeks': 1},
        {'days': -1},
        {'days': 1.5},
        {'days': None},
    ],
)
def test_duration_is_refused(written: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Duration.model_validate(written)
