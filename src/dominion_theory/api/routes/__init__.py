from fastapi import APIRouter

from ..schemas import Message
from . import basics, games, stream

REFUSALS: dict[int | str, dict[str, object]] = {status: {'model': Message} for status in (400, 404, 409, 422)}

router = APIRouter(responses=REFUSALS)
router.include_router(basics.router)
router.include_router(games.router)
router.include_router(stream.router)

__all__ = ['router']
