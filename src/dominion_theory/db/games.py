"""
Writing a row of the index of games.
"""

from sqlmodel import Session, select

from ..core.errors import DominionError
from .models import Game, Profile
from .profiles import PROFILE_NOT_FOUND


def add_game(session: Session, game: Game) -> Game:
    # The profile is locked first, so it cannot be removed under the new row.
    held = select(Profile.id).where(Profile.id == game.profile_id).with_for_update(read=True, key_share=True)
    if session.exec(held).first() is None:
        raise DominionError(PROFILE_NOT_FOUND, id=game.profile_id)
    session.add(game)
    session.commit()
    return game
