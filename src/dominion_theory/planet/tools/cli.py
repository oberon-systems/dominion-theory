"""
Dominion Theory: Maps: Tools: CLI

    Draws what the planet makes of a seed: the first window or the whole planet, biomes or properties.
"""

import json
import secrets
from pathlib import Path
from typing import Any

import click

from ...content import LAYERS, Params, load_params
from ...core.errors import DominionError
from .. import Planet, Region, place
from ..window import misses, tries
from . import pictures
from .screen import save
from .screen import show as opened

ERA = 'band'
BIOMES = 'biomes'
ALL = 'all'
SEEDS = 2**32


def _overrides(given: tuple[str, ...]) -> dict[str, Any]:
    read: dict[str, Any] = {}
    for item in given:
        path, found, value = item.partition('=')
        if not path or not found:
            raise click.BadParameter(f'{item} is not PATH=VALUE', param_hint='--set')
        try:
            read[path] = json.loads(value)
        except ValueError:
            read[path] = value
    return read


def _params(preset: str | None, given: tuple[str, ...]) -> Params:
    try:
        return load_params(preset, _overrides(given))
    except DominionError as error:
        raise click.ClickException(f'{error.key}: {error.values}') from error


def _drawn(params: Params, region: Region, show: str, season: str | None) -> pictures.Picture:
    names = params.eras[ERA].properties
    if show == BIOMES:
        return pictures.biomes(params, region)
    if show == ALL:
        return pictures.tiled([pictures.shaded(pictures.values(params, ERA, name, region, season)) for name in names])
    if show not in names:
        raise click.BadParameter(f'{show} is not {BIOMES}, {ALL} or one of {", ".join(names)}', param_hint='--show')
    return pictures.shaded(pictures.values(params, ERA, show, region, season))


def _report(params: Params, region: Region) -> None:
    found = pictures.shares(params, region)
    land = 1.0 - found.get('water', 0.0)
    click.echo(f'{"biome":<10} {"of all":>7} {"of land":>8}')
    for name, share in found.items():
        of_land = f' {share / land:8.1%}' if land and name != 'water' else ''
        click.echo(f'{name:<10} {share:7.1%}{of_land}')
    click.echo(f'cells with a river: {float(region.rivers.mean()):.1%}')
    click.echo(f'square corners of the shore: {pictures.corners(region.elevation <= 0)}')


@click.command()
@click.option('--seed', type=click.IntRange(min=0), help='Seed of the planet; drawn when left out.')
@click.option('--preset', help='Preset of the parameters.')
@click.option('--set', 'given', multiple=True, metavar='PATH=VALUE', help='Override one parameter.')
@click.option('--planet', 'whole', is_flag=True, help='Draw the whole planet instead of the first window.')
@click.option('--cell-km', type=click.IntRange(min=1), default=50, show_default=True, help='Cell of the whole planet.')
@click.option('--show', default=BIOMES, show_default=True, help=f'{BIOMES}, a property of the era, or {ALL}.')
@click.option('--season', help='Season the properties are worked out for; none when left out.')
@click.option('--scale', type=click.IntRange(min=1), default=2, show_default=True, help='Pixels to a side of a cell.')
@click.option('--out', type=click.Path(dir_okay=False, path_type=Path), help='Write the picture here, open no window.')
def cli(
    seed: int | None,
    preset: str | None,
    given: tuple[str, ...],
    whole: bool,
    cell_km: int,
    show: str,
    season: str | None,
    scale: int,
    out: Path | None,
) -> None:
    """
    Draw a map of a seed, as a game with the same preset and overrides would get it.
    """
    params = _params(preset, given)
    seed = secrets.randbelow(SEEDS) if seed is None else seed
    if season is not None and season not in [held.name for held in params.time.seasons]:
        raise click.BadParameter(f'{season} is not a season of the tree', param_hint='--season')

    planet = Planet(seed, params)
    window = params.planet.window
    band_km = params.eras[ERA].cell_km
    x, y = place(seed, params)
    places = tries(seed, params)
    order = f'try {places.index((x, y)) + 1} of {len(places)}' if (x, y) in places else 'given by hand'
    missed = misses(planet.skeleton, planet.rivers, params, x, y)
    click.echo(
        f'seed {seed}: the window at {x}, {y}, {order}, {missed} needs missed, {len(planet.rivers.lines)} rivers'
    )

    if whole:
        if planet.circumference_km % (2 * cell_km):
            raise click.BadParameter('the planet is not made of whole cells of this size', param_hint='--cell-km')
        across = planet.circumference_km // cell_km
        west, north = 0, 0
        region = planet.read(west, north, across, across // 2, cell_km)
    else:
        cell_km, west, north = band_km, x, y
        region = planet.read(x, y, window.width, window.height, band_km)

    picture = _drawn(params, region, show, season)
    if whole and show != ALL:
        frame = (value * band_km // cell_km for value in (x, y, window.width, window.height))
        picture = pictures.framed(picture, *frame)
    picture = pictures.enlarged(picture, scale)
    _report(params, region)

    if out is not None:
        save(picture, out)
        click.echo(f'written to {out}')
        return

    held = {name: pictures.values(params, ERA, name, region, season) for name in params.eras[ERA].properties}

    def describe(left: int, top: int) -> list[str]:
        row, column = top // scale, left // scale
        if show == ALL or not (0 <= row < region.biomes.shape[0] and 0 <= column < region.biomes.shape[1]):
            return []
        return [
            f'cell {west + column}, {north + row}',
            f'biome: {planet.biomes[int(region.biomes[row, column])]}',
            f'river: {"yes" if region.rivers[row, column] else "no"}',
            *(f'{name}: {amounts[row, column]:.2f}' for name, amounts in held.items()),
            *(f'{layer}: {getattr(region, layer)[row, column]:.2f}' for layer in LAYERS),
        ]

    found = pictures.shares(params, region)
    legend = [(None, f'seed {seed}, cells of {cell_km} km'), (None, season or 'no season'), (None, '')]
    legend += [(pictures.rgb(params.biomes[name].colour), f'{name} {found[name]:.1%}') for name in planet.biomes]
    legend.append((pictures.rgb(pictures.RIVER), f'river {float(region.rivers.mean()):.1%}'))
    opened(picture, f'seed {seed}: {show}', legend, describe, scale)
