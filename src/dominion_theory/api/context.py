"""
What every route works with: the settings, the runner service, the database and the index.
"""

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Query
from starlette.requests import HTTPConnection

from ..core.errors import DominionError
from ..core.settings import Settings
from ..db import Database
from ..runner import GAME_ENDED, GAME_NOT_FOUND, Runner, Service
from .errors import REQUEST_UNREADABLE
from .index import Index
from .schemas import View


@dataclass(frozen=True)
class Context:
    settings: Settings
    service: Service
    database: Database
    index: Index

    def runner(self, game_id: str) -> Runner:
        """
        The live game. One the index knows as finished has ended; any other is not found.
        """
        try:
            return self.service.find(game_id)
        except DominionError as error:
            if error.key == GAME_NOT_FOUND and self.index.find(game_id).finished_at is not None:
                raise DominionError(GAME_ENDED, id=game_id) from error
            raise

    def check_view(self, view: View) -> View:
        if view is View.SPECTATOR and not self.settings.spectator:
            raise DominionError(REQUEST_UNREADABLE)
        return view


def get_context(connection: HTTPConnection) -> Context:
    return cast(Context, connection.app.state.context)


def get_view(context: Annotated[Context, Depends(get_context)], view: Annotated[View, Query()] = View.SEAT) -> View:
    return context.check_view(view)


Ctx = Annotated[Context, Depends(get_context)]
Seen = Annotated[View, Depends(get_view)]
