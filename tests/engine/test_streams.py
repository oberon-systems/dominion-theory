import ast
import json
from pathlib import Path

from dominion_theory.engine.streams import Streams

SOURCE = Path(__file__).parents[2] / 'src' / 'dominion_theory'
SEEDED = {'Generator', 'PCG64', 'SeedSequence', 'default_rng'}


def unseeded(path: Path) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import) and any(alias.name == 'random' for alias in node.names):
            found.append('random')
        elif isinstance(node, ast.ImportFrom) and node.module in ('random', 'numpy.random'):
            found.append(node.module)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == 'random'
            and node.attr not in SEEDED
        ):
            found.append(f'random.{node.attr}')
    return found


def test_same_seed_and_name_give_the_same_numbers() -> None:
    assert Streams(5)['alpha'].random(4).tolist() == Streams(5)['alpha'].random(4).tolist()


def test_other_seed_or_name_gives_other_numbers() -> None:
    drawn = {Streams(seed)[name].random() for seed in (5, 6) for name in ('alpha', 'beta')}

    assert len(drawn) == 4


def test_draw_in_one_stream_does_not_shift_another() -> None:
    streams = Streams(5)
    streams['alpha'].random(100)

    assert streams['beta'].random() == Streams(5)['beta'].random()


def test_draw_zero_is_the_seed_alone_and_another_draw_gives_other_numbers() -> None:
    drawn = [Streams(5, draw=draw)['alpha'].random() for draw in (0, 1, 2)]

    assert drawn[0] == Streams(5)['alpha'].random()
    assert len(set(drawn)) == 3


def test_a_stream_made_after_its_states_were_carried_keeps_the_draw() -> None:
    streams = Streams(5, draw=3)
    streams['alpha'].random(3)

    carried = Streams(5, json.loads(json.dumps(streams.states())), draw=3)

    assert carried['beta'].random() == Streams(5, draw=3)['beta'].random() != Streams(5)['beta'].random()


def test_states_carry_a_stream_on() -> None:
    streams = Streams(5)
    streams['alpha'].random(3)

    carried = Streams(5, json.loads(json.dumps(streams.states())))

    assert list(streams.states()) == ['alpha']
    assert carried['alpha'].random() == streams['alpha'].random()


def test_engine_and_planet_draw_from_no_global_generator() -> None:
    found = {
        str(path.relative_to(SOURCE)): unseeded(path)
        for package in ('engine', 'planet')
        for path in sorted((SOURCE / package).rglob('*.py'))
    }

    assert {name: uses for name, uses in found.items() if uses} == {}


def test_global_generator_is_found(tmp_path: Path) -> None:
    module = tmp_path / 'alpha.py'
    module.write_text('import random\nimport numpy as np\nx = np.random.randint(3)\ny = np.random.default_rng(1)\n')

    assert unseeded(module) == ['random', 'random.randint']
