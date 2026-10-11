import numpy as np

from dominion_theory.engine.hashing import digest

GRID = np.arange(12, dtype=np.float64).reshape(3, 4) / 7


def test_hash_does_not_depend_on_the_order_of_names() -> None:
    assert digest({'alpha': 1, 'beta': [1, 2]}, {}) == digest({'beta': [1, 2], 'alpha': 1}, {})


def test_numbers_are_rounded_before_hashing() -> None:
    assert digest({'alpha': 0.1 + 0.2}, {}) == digest({'alpha': 0.3}, {})
    assert digest({'alpha': {'beta': -0.0}}, {}) == digest({'alpha': {'beta': 0.0}}, {})
    assert digest({}, {'alpha': GRID + 1e-9}) == digest({}, {'alpha': GRID})
    assert digest({'alpha': 0.3}, {}) != digest({'alpha': 0.30001}, {})


def test_hash_does_not_depend_on_the_byte_order_or_layout() -> None:
    assert digest({}, {'alpha': GRID.astype('>f8')}) == digest({}, {'alpha': GRID})
    assert digest({}, {'alpha': np.asfortranarray(GRID)}) == digest({}, {'alpha': GRID})


def test_hash_follows_the_grids() -> None:
    cells = np.zeros((2, 3), dtype=np.uint8)
    other = cells.copy()
    other[1, 2] = 1

    assert digest({}, {'alpha': cells}) != digest({}, {'alpha': other})
    assert digest({}, {'alpha': cells}) != digest({}, {'beta': cells})
    assert digest({}, {'alpha': cells}) != digest({}, {'alpha': cells.reshape(3, 2)})
    assert digest({}, {'alpha': cells}) != digest({}, {'alpha': cells.astype(np.int16)})
