"""
Dominion Theory: Maps

    Base biomes settings module

"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Biome:
    """
    Biome Base Class
    """

    def __repr__(self):
        return self.__class__.__name__.lower()

    def __lt__(self, other):
        return repr(self) < repr(other)

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))


@dataclass(frozen=True)
class BiomeProperties:
    """
    Biome Properties Base Class
    """
    # basic resources
    water: float
    food: float

    # features
    threat: float
    passability: float


@dataclass(frozen=True)
class Moisture:
    """
    Moisture Base Class
    """
    min: float
    max: float


@dataclass(frozen=True)
class Elevation:
    """
    Elevation Base Class
    """
    min: float
    max: float
