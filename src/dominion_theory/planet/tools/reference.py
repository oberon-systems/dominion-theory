"""
Dominion Theory: Maps: Tools: Reference

    What the planet of the defaults looks like for a few seeds, kept in a file so that a change of it is seen.
"""

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import click

from ...content import Params, load_params
from .. import Planet, place
from ..window import misses, tries
from . import pictures

ERA = 'band'
SEEDS = (1, 2, 3)
SOURCE = Path(__file__).parents[1]


def inputs(params: Params) -> str:
    """
    One hash of all a map follows from: the tree of parameters and the code of the planet.
    """
    held = sha256(params.hash.encode())
    for path in sorted(SOURCE.glob('*.py')):
        held.update(path.read_bytes())
    return held.hexdigest()


def survey(seed: int, params: Params) -> dict[str, Any]:
    """
    The planet of a seed in numbers: where the window lies, the rivers, the shares of biomes, every cell as a hash.
    """
    planet = Planet(seed, params)
    window = params.planet.window
    x, y = place(seed, params)
    places = tries(seed, params)
    coarse_km = params.planet.skeleton_km
    across = planet.circumference_km // coarse_km
    whole = planet.read(0, 0, across, across // 2, coarse_km)
    played = planet.read(x, y, window.width, window.height, params.eras[ERA].cell_km)
    return {
        'window': [x, y],
        'try': places.index((x, y)) + 1 if (x, y) in places else 0,
        'missed': misses(planet.skeleton, planet.rivers, params, x, y),
        'rivers': len(planet.rivers.lines),
        'river_cells': round(float(whole.rivers.mean()), 4),
        'shares': {name: round(share, 4) for name, share in pictures.shares(params, whole).items()},
        'planet': sha256(whole.biomes.tobytes() + whole.rivers.tobytes()).hexdigest(),
        'played': sha256(played.biomes.tobytes() + played.rivers.tobytes()).hexdigest(),
    }


def drawn(params: Params) -> dict[str, Any]:
    return {'inputs': inputs(params), 'seeds': {str(seed): survey(seed, params) for seed in SEEDS}}


def moved(old: dict[str, Any], new: dict[str, Any], path: str = '') -> list[str]:
    """
    Every value that differs between two surveys, as a line: where, what it was, what it is.
    """
    lines = []
    for name in sorted(old.keys() | new.keys()):
        was, now = old.get(name), new.get(name)
        if isinstance(was, dict) and isinstance(now, dict):
            lines += moved(was, now, f'{path}{name}.')
        elif was != now:
            lines.append(f'{path}{name}: {was} -> {now}')
    return lines


@click.command()
@click.argument('path', type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def cli(ctx: click.Context, path: Path) -> None:
    """
    Rewrite the reference when the parameters or the code of the planet changed, and say what moved on the maps.
    """
    params = load_params()
    kept = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'inputs': None, 'seeds': {}}
    if kept['inputs'] == inputs(params):
        return

    found = drawn(params)
    path.write_text(json.dumps(found, indent=2) + '\n', encoding='utf-8')
    lines = moved(kept['seeds'], found['seeds'])
    click.echo(f'the planet changed, {path} is rewritten: {len(lines)} values moved')
    for line in lines:
        click.echo(f'  {line}')
    ctx.exit(1)


if __name__ == '__main__':
    cli()
