"""
A stock: per resource, its lots of the day they came, the amount and for goods with one the quality, held by
anyone, as docs/game/skills.md, Stocks and holders, states it.
"""

from collections.abc import Mapping
from typing import Any

from ..content import Resource

type Lot = list[float]

# What is left of a lot below this is nothing: the steps of a float are not an amount.
NOTHING = 1e-9


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

    def add(self, name: str, day: int, amount: float, quality: float | None = None) -> None:
        """
        Puts an amount in: into the lot of the same day and quality, or a new lot.
        """
        lots = self.setdefault(name, [])
        for lot in reversed(lots):
            if lot[0] != day:
                break
            if _quality(lot) == quality:
                lot[1] += amount
                return
        lots.append([float(day), amount] if quality is None else [float(day), amount, quality])

    def join(self, other: Stock) -> None:
        """
        Puts every lot of another stock in, into the lot of its day and quality or where its day falls.
        """
        for name, lots in other.items():
            held = self.setdefault(name, [])
            for lot in lots:
                same = next((mine for mine in held if mine[0] == lot[0] and _quality(mine) == _quality(lot)), None)
                if same is None:
                    held.append(list(lot))
                else:
                    same[1] += lot[1]
            held.sort(key=lambda lot: lot[0])

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
        self[name] = [lot for lot in lots if lot[1] > NOTHING]
        return missing

    def part(self, name: str, wanted: float) -> Stock:
        """
        Takes up to an amount out as its own stock, the oldest lots first, each with its day and quality.
        """
        parted = Stock()
        missing = wanted
        for lot in self.get(name, []):
            taken = min(lot[1], missing)
            if taken > 0:
                parted.setdefault(name, []).append([lot[0], taken, *lot[2:]])
            lot[1] -= taken
            missing -= taken
        if name in self:
            self[name] = [lot for lot in self[name] if lot[1] > NOTHING]
        return parted

    def spoil(self, day: int, keeps: Mapping[str, int], ages: float = 1.0) -> dict[str, float]:
        """
        A day passed: drops the lots older than the days their resource keeps, whatever their quality; a resource
        with no days given never spoils. A day at a slower pace makes every lot younger by what it did not age, so
        a pace counts for the days it held only. Gives what was dropped.
        """
        dropped: dict[str, float] = {}
        for name in list(self):
            if name not in keeps:
                continue
            kept: list[Lot] = []
            gone = 0.0
            for lot in self[name]:
                lot[0] += 1.0 - ages
                if day - lot[0] < keeps[name]:
                    kept.append(lot)
                else:
                    gone += lot[1]
            if gone > 0:
                dropped[name] = gone
            self[name] = kept
        return dropped

    def wear(self, name: str, uses: float, serves: float) -> tuple[float, float]:
        """
        Wears a good by its uses, the oldest lots first: a unit of quality 1 serves that many, one of a lower quality
        that share. Gives the amount worn out and the uses no lot was left to serve.
        """
        worn = 0.0
        for lot in self.get(name, []):
            if uses <= 0:
                break
            served = serves * (1.0 if len(lot) < 3 else lot[2])
            taken = min(lot[1], uses / served)
            lot[1] -= taken
            worn += taken
            uses -= taken * served
        if name in self:
            self[name] = [lot for lot in self[name] if lot[1] > NOTHING]
        return worn, max(uses, 0.0)


def _quality(lot: Lot) -> float | None:
    return lot[2] if len(lot) > 2 else None
