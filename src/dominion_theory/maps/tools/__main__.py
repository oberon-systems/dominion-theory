"""
Dominion Theory: Maps: Tools CLI

    Provides some CLI Tools for visualize generated maps.

"""

import click

from .. import atlas, settings
from .visualize import visualize, visualize_all_properties, visualize_property


def get_properties() -> list:
    """
    Collect properties names
    """
    # pylint: disable-next=unnecessary-comprehension
    return [p for p in settings.biomes.grass.properties.__dict__]


@click.group()
@click.option('--height', default=512, help='Map height')
@click.option('--width', default=512, help='Map width')
@click.option('--seed', default=None, help='Random seed')
@click.pass_context
def cli(ctx, height: int, width: int, seed: int | None):
    """
    Base CLI definition
    """
    ctx.ensure_object(dict)
    ctx.obj['height'] = height
    ctx.obj['width'] = width
    ctx.obj['seed'] = seed


@cli.command(help='Simple map visualization')
@click.option('--scale', default=5, help='Map scaling factor')
@click.pass_context
def simple(ctx, scale: int):
    """
    Show simple visualisation
    """
    settings.height = ctx.obj['height']
    settings.width = ctx.obj['width']
    settings.seed = ctx.obj['seed']
    click.echo(
        f'Generating simple map '
        f'({settings.height}x{settings.width}, '
        f'seed {settings.seed})',
    )
    visualize(atlas(), scale)


@cli.command(name='property', help='Show map visualization for some property')
@click.option(
    '--name',
    'name',
    type=click.Choice(get_properties() + ['ALL']),
    default='ALL',
    help='Which property to show, defaults to all (chart)',
)
@click.pass_context
def show_property(ctx, name: str):
    """
    Show visualisation for some property or chart (default)
    """
    settings.height = ctx.obj['height']
    settings.width = ctx.obj['width']
    settings.seed = ctx.obj['seed']

    if name != 'ALL':
        click.echo(
            f'Generating {name} map '
            f'({settings.height}x{settings.width}, '
            f'seed {settings.seed})',
        )
        visualize_property(atlas(), name)

    else:
        click.echo(
            f'Generating maps for all properties '
            f'({settings.height}x{settings.width}, '
            f'seed {settings.seed})',
        )
        visualize_all_properties(atlas())


if __name__ == '__main__':
    # pylint: disable-next=no-value-for-parameter
    cli()
