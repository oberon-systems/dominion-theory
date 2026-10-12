"""
The database named by DT_DATABASE_URL: its sessions and its migrations.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from ..core.settings import get_settings

MIGRATIONS = Path(__file__).parent / 'migrations'


class Database:
    def __init__(self, url: str | None = None) -> None:
        self.engine = create_engine(url or get_settings().database_url)
        path = self.engine.url.database
        if self.engine.dialect.name == 'sqlite' and path and path != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)

    def session(self) -> Session:
        return Session(self.engine, expire_on_commit=False)

    def upgrade(self, revision: str = 'head') -> None:
        config = Config()
        config.set_main_option('script_location', str(MIGRATIONS))
        with self.engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, revision)
