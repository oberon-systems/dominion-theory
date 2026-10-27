import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = 'dominion_theory'
SOURCE = Path(__file__).parents[1] / 'src' / ROOT

# The table Packages of docs/architecture/overview.md, column "May import".
ALLOWED: dict[str, set[str]] = {
    'core': set(),
    'content': {'core'},
    'planet': {'core', 'content'},
    'engine': {'core', 'content', 'planet'},
    'players': {'engine', 'content'},
    'i18n': {'core'},
    'store': {'core'},
    'db': {'core'},
    'runner': {'engine', 'store', 'content'},
    'api': {'runner', 'engine', 'db', 'i18n'},
    'lab': {'players', 'runner', 'content', 'i18n', 'client'},
    'client': {'i18n', 'runner'},
}


def imported(tree: ast.Module, package: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield tuple(alias.name.split('.'))
        elif isinstance(node, ast.ImportFrom):
            base = package[: len(package) - node.level + 1] if node.level else ()
            target = base + tuple(node.module.split('.')) if node.module else base
            if target == (ROOT,):
                for alias in node.names:
                    yield (ROOT, alias.name)
            else:
                yield target


def violations(source: Path) -> list[str]:
    found = []
    for path in sorted(source.rglob('*.py')):
        parts = path.relative_to(source).parts
        if len(parts) == 1:
            continue
        owner = parts[0]
        # core holds settings, logging and errors, so every package may import it.
        allowed = ALLOWED.get(owner, set()) | {owner, 'core'}
        for target in imported(ast.parse(path.read_text()), (ROOT, *parts[:-1])):
            if target[0] == ROOT and len(target) > 1 and target[1] not in allowed:
                found.append(f'{"/".join(parts)}: {owner} imports {target[1]}')
    return found


def test_imports_go_down_only() -> None:
    assert violations(SOURCE) == []


def test_every_package_is_in_the_table() -> None:
    packages = {path.parent.name for path in SOURCE.glob('*/__init__.py')}

    assert packages <= ALLOWED.keys()


@pytest.mark.parametrize(
    ('owner', 'line', 'target'),
    [
        ('engine', 'from dominion_theory.api import application', 'api'),
        ('engine', 'from ..store import Store', 'store'),
        ('engine', 'import dominion_theory.db.models', 'db'),
        ('engine', 'from .. import i18n', 'i18n'),
        ('api', 'from dominion_theory.store import Store', 'store'),
        ('core', 'from ..content import registry', 'content'),
        ('store', 'def late() -> None:\n    from ..engine import Game', 'engine'),
        ('client', 'from ..api import create_app', 'api'),
        ('client', 'from dominion_theory.engine import Game', 'engine'),
        ('client', 'import dominion_theory.db', 'db'),
    ],
)
def test_forbidden_import_is_found(tmp_path: Path, owner: str, line: str, target: str) -> None:
    module = tmp_path / owner / 'alpha.py'
    module.parent.mkdir()
    module.write_text(line + '\n')

    assert violations(tmp_path) == [f'{owner}/alpha.py: {owner} imports {target}']


@pytest.mark.parametrize(
    ('owner', 'line'),
    [
        ('engine', 'from ..planet import atlas'),
        ('engine', 'from . import clock'),
        ('runner', 'from dominion_theory.core.settings import get_settings'),
        ('api', 'import dominion_theory.runner'),
        ('api', 'import json'),
        ('client', 'from ..i18n import render'),
        ('client', 'from ..runner import replay'),
    ],
)
def test_allowed_import_is_not_reported(tmp_path: Path, owner: str, line: str) -> None:
    module = tmp_path / owner / 'alpha.py'
    module.parent.mkdir()
    module.write_text(line + '\n')

    assert violations(tmp_path) == []
