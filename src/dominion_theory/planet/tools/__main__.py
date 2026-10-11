"""
Dominion Theory: Maps: Tools CLI

    Provides some CLI Tools for visualize generated maps.

"""

import secrets

import click
import numpy as np

from .. import atlas, settings
from .visualize import visualize, visualize_all_properties, visualize_property


def world(ctx) -> np.ndarray:
    """
    Generate the map the options ask for
    """
    size = {'height': ctx.obj['height'], 'width': ctx.obj['width']}
    return atlas(seed=ctx.obj['seed'], rivers=np.random.default_rng(ctx.obj['seed']), **size)


def label(ctx) -> str:
    return f'({ctx.obj["height"]}x{ctx.obj["width"]}, seed {ctx.obj["seed"]})'


def get_properties() -> list:
    """
    Collect properties names
    """
    return [p for p in settings.biomes.grass.properties.__dict__]


@click.group()
@click.option('--height', default=128, help='Map height')
@click.option('--width', default=128, help='Map width')
@click.option('--seed', default=0, help='Random seed')
@click.pass_context
def cli(ctx, height: int, width: int, seed: int):
    """
    Base CLI definition
    """
    ctx.ensure_object(dict)
    ctx.obj['height'] = height
    ctx.obj['width'] = width

    ctx.obj['seed'] = seed if seed else secrets.randbelow(65534)


@cli.command(help='Simple map visualization')
@click.option('--scale', default=4, help='Map scaling factor')
@click.pass_context
def simple(ctx, scale: int):
    """
    Show simple visualisation
    """
    click.echo(f'Generating simple map {label(ctx)}')
    visualize(world(ctx), scale)


@cli.command(name='property', help='Show map visualization for some property')
@click.option(
    '--name',
    'name',
    type=click.Choice(get_properties() + ['ALL']),
    default='ALL',
    help='Which property to show, defaults to all (chart)',
)
@click.option('--scale', default=4, help='Map scaling factor')
@click.pass_context
def show_property(ctx, name: str, scale: int):
    """
    Show visualisation for some property or chart (default)
    """
    if name != 'ALL':
        click.echo(f'Generating {name} map {label(ctx)}')
        visualize_property(world(ctx), name, scale)

    else:
        click.echo(f'Generating maps for all properties {label(ctx)}')
        visualize_all_properties(world(ctx), scale)


if __name__ == '__main__':
    cli()
