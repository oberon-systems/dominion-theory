"""
Games: created, listed, read, commanded, clocked and ended. Every one of them goes through its runner.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import FileResponse

from ...core.errors import DominionError
from ...runner import RECORD_UNREADABLE, Runner
from .. import schemas
from ..biomes import described
from ..commands import read_command
from ..context import Context, Ctx, Seen
from ..maps import rectangle, remembered

RECORD_TYPE = 'application/gzip'

router = APIRouter(prefix='/games')

Edge = Annotated[int | None, Query()]
Side = Annotated[int | None, Query(ge=0)]


def _described(runner: Runner) -> schemas.Game:
    return schemas.Game(
        id=runner.id,
        seed=runner.game.seed,
        params_hash=runner.game.params.hash,
        mode=runner.mode,
        running=runner.running,
        date=schemas.Date(**asdict(runner.game.date)),
    )


def _row(context: Context, game_id: str) -> schemas.Row:
    return schemas.Row.model_validate(context.index.find(game_id), from_attributes=True)


@router.post('', status_code=201)
async def create(body: schemas.NewGame, context: Ctx) -> schemas.Game:
    service = context.service
    runner = service.create(body.seed, body.preset, body.overrides, body.mode, seated=body.seated)
    context.index.add(runner, body.preset)
    return _described(runner)


@router.get('')
async def listed(context: Ctx) -> schemas.Games:
    rows = [schemas.Row.model_validate(row, from_attributes=True) for row in context.index.rows()]
    return schemas.Games(games=rows)


@router.get('/{game_id}')
async def game(game_id: str, context: Ctx) -> schemas.Game:
    return _described(context.runner(game_id))


@router.delete('/{game_id}')
async def end(game_id: str, context: Ctx) -> schemas.Row:
    context.runner(game_id)
    context.service.end(game_id)
    return _row(context, game_id)


@router.get('/{game_id}/params')
async def params(game_id: str, context: Ctx) -> dict[str, Any]:
    return context.runner(game_id).game.params.tree()


@router.get('/{game_id}/snapshot')
async def snapshot(game_id: str, context: Ctx, view: Seen) -> schemas.Snapshot:
    return schemas.Snapshot(**context.runner(game_id).snapshot())


@router.get('/{game_id}/biomes')
async def biomes(game_id: str, context: Ctx, view: Seen) -> schemas.Biomes:
    return schemas.Biomes(**described(context.runner(game_id).game))


@router.get('/{game_id}/map')
async def map_part(
    game_id: str,
    context: Ctx,
    view: Seen,
    x: Edge = None,
    y: Edge = None,
    width: Side = None,
    height: Side = None,
    known: Edge = None,
) -> schemas.Map:
    game = context.runner(game_id).game
    if known is None:
        return schemas.Map(**rectangle(game, x, y, width, height))
    return schemas.Map(**remembered(game, known, x, y, width, height))


@router.post('/{game_id}/commands')
async def command(game_id: str, envelope: Annotated[dict[str, Any], Body()], context: Ctx) -> schemas.Taken:
    runner = context.runner(game_id)
    taken = read_command(runner.game.seats[0], envelope)
    runner.submit(taken)
    return schemas.Taken(id=str(taken.id))


@router.post('/{game_id}/clock')
async def clock(game_id: str, body: schemas.ClockRequest, context: Ctx) -> schemas.Game:
    runner = context.runner(game_id)
    if body.action == 'pause':
        runner.pause()
    elif body.action == 'resume':
        runner.resume()
    elif body.action == 'step':
        runner.step()
    elif body.value is not None:
        runner.set_speed(body.value)
    return _described(runner)


@router.get('/{game_id}/record', response_class=FileResponse)
async def record(game_id: str, context: Ctx) -> FileResponse:
    path = Path(context.index.find(game_id).record_path)
    if not path.is_file():
        raise DominionError(RECORD_UNREADABLE, path=path.name)
    return FileResponse(path, media_type=RECORD_TYPE, filename=path.name)
