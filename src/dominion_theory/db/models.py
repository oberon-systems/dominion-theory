"""
The tables: plain, tied by value columns, with no relation between them.
"""

import time

from sqlmodel import BigInteger, Field, SQLModel

METADATA = SQLModel.metadata


def now() -> int:
    return int(time.time())


class Profile(SQLModel, table=True):
    """
    The person who plays.
    """

    __tablename__ = 'profiles'

    id: str = Field(primary_key=True, max_length=32)
    name: str = Field(max_length=64)
    locale: str = Field(max_length=8)
    created_at: int = Field(default_factory=now, sa_type=BigInteger)


class Game(SQLModel, table=True):
    """
    One row of the index of games: a pointer to a run record and a summary of it.
    """

    __tablename__ = 'games'

    id: str = Field(primary_key=True, max_length=32)
    profile_id: str = Field(max_length=32, index=True)
    seed: int = Field(sa_type=BigInteger)
    params_hash: str = Field(max_length=64)
    preset: str | None = Field(default=None, max_length=64)
    started_at: int = Field(default_factory=now, sa_type=BigInteger)
    finished_at: int | None = Field(default=None, sa_type=BigInteger)
    outcome: str | None = Field(default=None, max_length=32)
    last_tick: int = 0
    record_path: str = Field(max_length=255)
