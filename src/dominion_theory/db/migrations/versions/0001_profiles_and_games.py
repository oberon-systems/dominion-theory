"""
Profiles and the index of games.
"""

from alembic import op
from sqlmodel import BigInteger, Column, Integer, String

revision = '0001'
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        'profiles',
        Column('id', String(length=32), primary_key=True),
        Column('name', String(length=64), nullable=False),
        Column('locale', String(length=8), nullable=False),
        Column('created_at', BigInteger(), nullable=False),
    )
    op.create_table(
        'games',
        Column('id', String(length=32), primary_key=True),
        Column('profile_id', String(length=32), nullable=False),
        Column('seed', BigInteger(), nullable=False),
        Column('params_hash', String(length=64), nullable=False),
        Column('preset', String(length=64), nullable=True),
        Column('started_at', BigInteger(), nullable=False),
        Column('finished_at', BigInteger(), nullable=True),
        Column('outcome', String(length=32), nullable=True),
        Column('last_tick', Integer(), nullable=False),
        Column('record_path', String(length=255), nullable=False),
    )
    op.create_index('ix_games_profile_id', 'games', ['profile_id'])


def downgrade() -> None:
    op.drop_index('ix_games_profile_id', table_name='games')
    op.drop_table('games')
    op.drop_table('profiles')
