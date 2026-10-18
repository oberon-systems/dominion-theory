"""
A stock: per resource, its lots of the day they came and the amount, held by anyone, as docs/game/skills.md,
Stocks and holders, states it.
"""

from collections.abc import Mapping
from typing import Any

from ..content import Resource

type Lot = list[float]


class Stock(dict[str, list[Lot]]):
    """
    The lots of every resource held, the oldest first.
    """

    @classmethod
    def read(cls, plain: Mapping[str, Any]) -> Stock:
        return cls({name: [list(lot) for lot in lots] for name, lots in plain.items()})

    def plain(self) -> dict[str, list[Lot]]:
        return {name: [list(lot) for lot in lots] for name, lots in sorted(self.items())}

    def held(self, name: str) -> float:
        return sum(lot[1] for lot in self.get(name, ()))

    def amounts(self) -> dict[str, float]:
        return {name: self.held(name) for name in sorted(self)}

    def weight(self, resources: Mapping[str, Resource]) -> float:
        return sum(self.held(name) * resources[name].weight_kg for name in self)

    def add(self, name: str, day: int, amount: float) -> None:
        """
        Puts an amount in: into the lot of the same day, or a new lot.
        """
        lots = self.setdefault(name, [])
        if lots and lots[-1][0] == day:
            lots[-1][1] += amount
        else:
            lots.append([float(day), amount])

    def take(self, name: str, wanted: float) -> float:
        """
        Takes up to an amount, the oldest lots first, and drops the lots emptied; gives what is still missing.
        """
        missing = wanted
        lots = self.get(name, [])
        for lot in lots:
            taken = min(lot[1], missing)
            lot[1] -= taken
            missing -= taken
        self[name] = [lot for lot in lots if lot[1] > 0]
        return missing

    def spoil(self, day: int, keeps: Mapping[str, int], ages: float = 1.0) -> None:
        """
        Drops the lots older than the days their resource keeps, aged at a pace.
        """
        for name in list(self):
            self[name] = [lot for lot in self[name] if (day - lot[0]) * ages < keeps[name]]
