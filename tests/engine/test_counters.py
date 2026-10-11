import pytest

from dominion_theory.engine.counters import Counters


def test_row_follows_the_order_of_declaration() -> None:
    kept = {'beta': 2, 'alpha': 1.5}
    counters = Counters()
    counters.declare('beta', lambda: kept['beta'])
    counters.declare('alpha', lambda: kept['alpha'])
    kept['beta'] = 7

    assert counters.names == ('beta', 'alpha')
    assert counters.row() == [7, 1.5]


def test_counter_is_declared_once() -> None:
    counters = Counters()
    counters.declare('alpha', lambda: 0)

    with pytest.raises(ValueError, match='alpha'):
        counters.declare('alpha', lambda: 1)
