"""
The state of cells: a stock per property, kept only where some stock is below full.
"""

from collections.abc import Callable, Iterable, Mapping
from typing import Any

Place = tuple[int, int]

# Shares of a recovery time do not always add up to exactly one.
FULL = 1.0 - 1e-9


def valued(base: float, modifiers: Iterable[Any], stock: float = 1.0) -> float:
    """
    A property of a cell: its base and every plus, times every times and the stock, held between 0 and 1.
    """
    plus, times = base, stock
    for modifier in modifiers:
        if modifier is not None and modifier.kind == 'plus':
            plus += modifier.amount
        elif modifier is not None:
            times *= modifier.amount
    return min(max(plus * times, 0.0), 1.0)


class Cells:
    """
    Stocks by planet cell. A stock that is full is not kept, and a cell with none kept is forgotten.
    """

    def __init__(self, kept: Iterable[Mapping[str, Any]] = ()) -> None:
        self._kept: dict[Place, dict[str, float]] = {}
        for cell in kept:
            for name, stock in cell['stocks'].items():
                self._hold((cell['x'], cell['y']), name, float(stock))

    def __len__(self) -> int:
        return len(self._kept)

    def stock(self, place: Place, name: str) -> float:
        return self._kept.get(place, {}).get(name, 1.0)

    def lower(self, place: Place, name: str, amount: float) -> None:
        self._hold(place, name, max(self.stock(place, name) - amount, 0.0))

    def regain(self, shares: Callable[[Place], Mapping[str, float]]) -> list[Place]:
        """
        Adds to every kept stock the share its cell regains in a tick; gives the cells that changed.
        """
        changed = sorted(self._kept)
        for place in changed:
            regained = shares(place)
            for name, stock in sorted(self._kept[place].items()):
                self._hold(place, name, stock + regained[name])
        return changed

    def plain(self) -> list[dict[str, Any]]:
        return [{'x': x, 'y': y, 'stocks': dict(sorted(self._kept[x, y].items()))} for x, y in sorted(self._kept)]

    def _hold(self, place: Place, name: str, stock: float) -> None:
        if stock < FULL:
            self._kept.setdefault(place, {})[name] = stock
            return
        stocks = self._kept.get(place, {})
        stocks.pop(name, None)
        if not stocks:
            self._kept.pop(place, None)
