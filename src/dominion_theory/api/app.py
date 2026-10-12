"""
The application: one factory, and what a server does when it starts and stops.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from ..core.settings import Settings, get_settings
from ..db import Database, local_profile
from ..runner import Service
from .context import Context
from .errors import install
from .index import Index
from .routes import router

PREFIX = '/api/v1'


def create_app(
    settings: Settings | None = None,
    service: Service | None = None,
    database: Database | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    database = database or Database(settings.database_url)
    context = Context(settings, service or Service(settings=settings), database, Index(database))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database.upgrade()
        with database.session() as session:
            local_profile(session)
        for runner in context.service.restore():
            context.index.follow(runner)
        yield
        for runner in context.service.games():
            runner.pause()

    app = FastAPI(
        title='Dominion Theory',
        version=version('dominion-theory'),
        lifespan=lifespan,
        openapi_url=f'{PREFIX}/openapi.json',
        docs_url=f'{PREFIX}/docs',
        redoc_url=None,
    )
    app.state.context = context
    install(app)
    app.include_router(router, prefix=PREFIX)
    return app
