"""
Server settings, read from the environment with the prefix DT_.
"""

import re
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SPAN_UNITS = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}


def _database_url(data: dict[str, Any]) -> str:
    return f'sqlite:///{data["data_dir"] / "dominion-theory.db"}'


def _records_dir(data: dict[str, Any]) -> Path:
    records: Path = data['data_dir'] / 'records'
    return records


class Settings(BaseSettings):
    """
    How the server runs. Nothing here can change the outcome of a game.
    """

    model_config = SettingsConfigDict(env_prefix='DT_', frozen=True)

    data_dir: Path = Path('data')
    store_url: str = ''
    store_ttl: timedelta = timedelta(days=7)
    database_url: str = Field(default_factory=_database_url)
    records_dir: Path = Field(default_factory=_records_dir)
    tick_ms: int = Field(default=500, gt=0)
    updates_kept: int = Field(default=512, gt=0)
    spectator: bool = True

    @field_validator('store_ttl', mode='before')
    @classmethod
    def _span(cls, value: object) -> object:
        if isinstance(value, str) and (found := re.fullmatch(r'(\d+)([smhd])', value.strip())):
            return timedelta(**{SPAN_UNITS[found[2]]: int(found[1])})
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
