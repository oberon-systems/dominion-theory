from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlmodel import inspect

from dominion_theory.core.settings import get_settings
from dominion_theory.db import METADATA, PROFILE_COLUMNS, Database


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(f'sqlite:///{tmp_path}/alpha.db')
    database.upgrade()
    return database


def test_the_migration_builds_both_tables(database: Database) -> None:
    assert set(inspect(database.engine).get_table_names()) == {'alembic_version', 'profiles', 'games'}


def test_the_schema_equals_the_models(database: Database) -> None:
    with database.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={'compare_type': True})

        assert compare_metadata(context, METADATA) == []


def test_migrating_twice_changes_nothing(database: Database) -> None:
    database.upgrade()

    assert set(inspect(database.engine).get_table_names()) == {'alembic_version', 'profiles', 'games'}


def test_the_schema_holds_no_foreign_key(database: Database) -> None:
    inspector = inspect(database.engine)

    assert [key for table in inspector.get_table_names() for key in inspector.get_foreign_keys(table)] == []
    assert [key for table in METADATA.tables.values() for key in table.foreign_keys] == []


def test_every_profile_column_is_in_the_list(database: Database) -> None:
    inspector = inspect(database.engine)
    found = {
        (table, column['name'])
        for table in inspector.get_table_names()
        for column in inspector.get_columns(table)
        if column['name'] == 'profile_id'
    }

    assert found == set(PROFILE_COLUMNS)


def test_the_default_database_lies_in_the_data_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('DT_DATA_DIR', str(tmp_path / 'alpha'))
    monkeypatch.delenv('DT_DATABASE_URL', raising=False)
    get_settings.cache_clear()

    try:
        database = Database()
    finally:
        get_settings.cache_clear()

    assert database.engine.url.database == f'{tmp_path}/alpha/dominion-theory.db'
    assert (tmp_path / 'alpha').is_dir()
