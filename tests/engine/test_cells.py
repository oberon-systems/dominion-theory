import pytest

from dominion_theory.engine.cells import Cells, Place


def test_an_untouched_cell_is_full_and_not_kept() -> None:
    cells = Cells()

    cells.lower((3, 4), 'food', 0.0)

    assert cells.stock((3, 4), 'food') == 1.0
    assert len(cells) == 0
    assert cells.plain() == []


def test_a_stock_is_lowered_and_not_below_nothing() -> None:
    cells = Cells()

    cells.lower((3, 4), 'food', 0.25)
    cells.lower((3, 4), 'food', 0.25)
    cells.lower((3, 4), 'water', 7.0)

    assert cells.stock((3, 4), 'food') == pytest.approx(0.5)
    assert cells.stock((3, 4), 'water') == 0.0
    assert cells.stock((4, 3), 'food') == 1.0
    assert len(cells) == 1


def test_regaining_drops_a_full_stock_and_forgets_an_empty_cell() -> None:
    cells = Cells()
    cells.lower((3, 4), 'food', 1.0)
    cells.lower((3, 4), 'water', 0.5)
    cells.lower((1, 9), 'food', 0.5)

    first = cells.regain(lambda place: {'food': 0.25, 'water': 0.5})
    kept = cells.plain()
    second = cells.regain(lambda place: {'food': 0.25, 'water': 0.5})

    assert first == [(1, 9), (3, 4)]
    assert kept == [
        {'x': 1, 'y': 9, 'stocks': {'food': 0.75}},
        {'x': 3, 'y': 4, 'stocks': {'food': 0.25}},
    ]
    assert second == [(1, 9), (3, 4)]
    assert cells.plain() == [{'x': 3, 'y': 4, 'stocks': {'food': 0.5}}]


def test_shares_that_do_not_add_up_exactly_still_fill_a_stock() -> None:
    cells = Cells()
    cells.lower((0, 0), 'food', 1.0)

    for _ in range(149):
        cells.regain(lambda place: {'food': 1 / 150})
    before = len(cells)
    cells.regain(lambda place: {'food': 1 / 150})

    assert (before, len(cells)) == (1, 0)


def test_cells_are_worked_through_by_coordinate() -> None:
    cells = Cells()
    asked: list[Place] = []

    def share(place: Place) -> dict[str, float]:
        asked.append(place)
        return {'food': 0.1}

    for place in [(5, 1), (2, 8), (2, 3), (9, 0)]:
        cells.lower(place, 'food', 0.5)
    cells.regain(share)

    assert asked == [(2, 3), (2, 8), (5, 1), (9, 0)]
    assert [(cell['x'], cell['y']) for cell in cells.plain()] == asked


def test_plain_cells_are_read_back() -> None:
    cells = Cells()
    cells.lower((5, 1), 'water', 0.3)
    cells.lower((5, 1), 'food', 0.6)
    cells.lower((2, 8), 'food', 0.1)

    copy = Cells(cells.plain())

    assert copy.plain() == cells.plain()
    assert list(cells.plain()[1]['stocks']) == ['food', 'water']
    assert Cells([{'x': 1, 'y': 1, 'stocks': {'food': 1.0}}]).plain() == []
