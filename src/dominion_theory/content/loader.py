"""
Builds a game's tree: defaults, then a preset, then overrides by path.
"""

import re
from collections.abc import Iterable, Iterator
from importlib.resources import files
from typing import Any

import yaml
from deepdiff import DeepDiff, Delta
from pydantic import ValidationError

from ..core.errors import DominionError
from .model import PARAMS_INVALID, Params

PRESET_NOT_FOUND = 'error-preset-not-found'
DATA = files('dominion_theory.content')
SPLIT = ('biomes', 'minds')
DIFF_STEP = re.compile(r"\['([^']*)'\]|\[(\d+)\]")

type Keys = tuple[str | int, ...]


def _child(node: Any, key: str | int) -> Any:
    try:
        return node[key]
    except KeyError, IndexError, TypeError:
        return None


def _dotted(keys: Iterable[str | int], tree: Any) -> str:
    names = []
    node = tree
    for key in keys:
        node = _child(node, key)
        named = isinstance(key, int) and isinstance(node, dict) and 'name' in node
        names.append(str(node['name'] if named else key))
    return '.'.join(names)


def _item_names(node: list[Any]) -> list[str | None]:
    return [item.get('name') if isinstance(item, dict) else None for item in node]


def _step(node: Any, name: str, path: str) -> str | int:
    known: list[str] = []
    if isinstance(node, dict):
        if name in node:
            return name
        known = sorted(node)
    elif isinstance(node, list):
        names = _item_names(node)
        if name in names:
            return names.index(name)
        if name.isdecimal() and int(name) < len(node):
            return int(name)
        known = [str(position if item is None else item) for position, item in enumerate(names)]
    expected = f'one of {", ".join(known)}' if known else 'no name below a value'
    raise DominionError(PARAMS_INVALID, path=path, found=name, expected=expected)


def _layer_changes(layer: Any, node: Any, keys: Keys, path: str) -> Iterator[tuple[Keys, Any]]:
    if isinstance(layer, dict) and isinstance(node, dict):
        for name, value in layer.items():
            below = f'{path}.{name}' if path else str(name)
            key = _step(node, str(name), below)
            yield from _layer_changes(value, node[key], (*keys, key), below)
    elif layer and isinstance(layer, list) and isinstance(node, list) and all(_item_names(layer) + _item_names(node)):
        for item in layer:
            below = f'{path}.{item["name"]}'
            key = _step(node, item['name'], below)
            rest = {name: value for name, value in item.items() if name != 'name'}
            yield from _layer_changes(rest, _child(node, key), (*keys, key), below)
    else:
        yield keys, layer


def _override_changes(overrides: dict[str, Any], tree: dict[str, Any]) -> Iterator[tuple[Keys, Any]]:
    for path, value in overrides.items():
        keys: Keys = ()
        node: Any = tree
        for name in path.split('.'):
            key = _step(node, name, path)
            keys = (*keys, key)
            node = node[key]
        yield keys, value


def _lay(tree: dict[str, Any], changes: Iterable[tuple[Keys, Any]]) -> dict[str, Any]:
    changed = {'root' + ''.join(f'[{key!r}]' for key in keys): {'new_value': value} for keys, value in changes}
    if not changed:
        return tree
    laid: dict[str, Any] = Delta({'values_changed': changed}, raise_errors=True) + tree
    return laid


def _read(folder: str, name: str) -> Any:
    return yaml.safe_load(DATA.joinpath(*folder.split('/'), f'{name}.yaml').read_text(encoding='utf-8'))


def _names(folder: str) -> list[str]:
    names = (entry.name for entry in DATA.joinpath(*folder.split('/')).iterdir())
    return sorted(name.removesuffix('.yaml') for name in names if name.endswith('.yaml'))


def _section(folder: str, name: str, section: str) -> Any:
    data = _read(folder, name)
    if not isinstance(data, dict) or list(data) != [section]:
        raise DominionError(PARAMS_INVALID, path=section, found=data, expected=f'a mapping with the key {section}')
    return data[section]


def _entries(section: str) -> dict[str, Any]:
    entries = {}
    for name in _names(f'defaults/{section}'):
        data = _section(f'defaults/{section}', name, section)
        if not isinstance(data, dict) or list(data) != [name]:
            path = f'{section}.{name}'
            raise DominionError(PARAMS_INVALID, path=path, found=data, expected=f'a mapping with the key {name}')
        entries[name] = data[name]
    return entries


def _defaults() -> dict[str, Any]:
    return {
        section: _entries(section) if section in SPLIT else _section('defaults', section, section)
        for section in Params.model_fields
    }


def presets() -> list[str]:
    return _names('presets')


def _resolve(tree: dict[str, Any]) -> Params:
    try:
        return Params.model_validate(tree)
    except ValidationError as error:
        first = error.errors()[0]
        path = _dotted(first['loc'], tree)
        raise DominionError(PARAMS_INVALID, path=path, found=first['input'], expected=first['msg']) from error


def load_params(preset: str | None = None, overrides: dict[str, Any] | None = None) -> Params:
    tree = _defaults()
    if preset is not None:
        if preset not in presets():
            raise DominionError(PRESET_NOT_FOUND, id=preset)
        tree = _lay(tree, _layer_changes(_read('presets', preset) or {}, tree, (), ''))
    if overrides:
        tree = _lay(tree, _override_changes(overrides, tree))
    return _resolve(tree)


def diff(a: Params, b: Params) -> dict[str, dict[str, Any]]:
    """
    What differs between two resolved trees, by dotted path: old, new or both.
    """
    old, new = a.tree(), b.tree()
    found: dict[str, dict[str, Any]] = {}
    for kind, entries in DeepDiff(old, new, verbose_level=2).items():
        for path, detail in entries.items():
            keys = [name or int(position) for name, position in DIFF_STEP.findall(path)]
            if kind.endswith('added'):
                found[_dotted(keys, new)] = {'new': detail}
            elif kind.endswith('removed'):
                found[_dotted(keys, old)] = {'old': detail}
            else:
                found[_dotted(keys, old)] = {'old': detail['old_value'], 'new': detail['new_value']}
    return dict(sorted(found.items()))
