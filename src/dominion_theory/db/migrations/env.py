"""
Run by Alembic: on the connection it is handed, or on the configured database.
"""

from typing import Any

from alembic import context

from dominion_theory.db.database import Database
from dominion_theory.db.models import METADATA


def run(connection: Any) -> None:
    context.configure(connection=connection, target_metadata=METADATA)
    with context.begin_transaction():
        context.run_migrations()


supplied = context.config.attributes.get('connection')
if supplied is None:
    with Database().engine.begin() as opened:
        run(opened)
else:
    run(supplied)
