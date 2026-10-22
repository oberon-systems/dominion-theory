"""
Which files that are not code each test module reads, so that make test runs, beside what testmon picks for the
code, the modules whose data changed: docs/dev/setup.md, Check. A file is kept by its sha256, a directory by its
sorted names; the record lies in .datamon.json.
"""

import hashlib
import json
import os
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
KEPT = ROOT / '.datamon.json'
OPTION = '--data-changed'
# Top-level folders whose files are no input of a test: runs, records and pictures; and every hidden one.
OUTSIDE = ('data', 'lives', 'maps')
CODE = ('.py', '.pyc')
EVENTS = ('open', 'os.listdir', 'os.scandir')
# Modules whose functools caches read files once a process: cleared before every test module.
CACHED = ('dominion_theory.i18n.catalogues',)

type Record = dict[str, dict[str, str]]


class Reading:
    """
    The files and folders the tests of one module have touched so far.
    """

    module: str | None = None
    touched: set[str] = set()


def relative(target: Any) -> str | None:
    """
    A path the tests touched, relative to the repository, when it is data of the repository.
    """
    if isinstance(target, int):
        return None
    try:
        path = os.path.abspath(os.fsdecode(target))
    except TypeError:
        return None
    if not path.startswith(f'{ROOT}{os.sep}') or path.endswith(CODE) or '__pycache__' in path:
        return None
    name = os.path.relpath(path, ROOT)
    top = name.split(os.sep)[0]
    return None if top in OUTSIDE or top.startswith('.') else name


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if Reading.module is not None and event in EVENTS and args:
        name = relative(args[0])
        if name is not None:
            Reading.touched.add(name)


def digest(name: str, root: Path = ROOT) -> str:
    """
    The sha256 of a file, of the sorted names of a folder, or nothing for a path that is gone.
    """
    path = root / name
    if path.is_dir():
        return hashlib.sha256('\n'.join(sorted(entry.name for entry in path.iterdir())).encode()).hexdigest()
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return ''


def changed(record: Record, root: Path = ROOT) -> set[str]:
    """
    The modules some file or folder of which is not what it was when they last ran.
    """
    digests: dict[str, str] = {}
    found = set()
    for module, read in record.items():
        for name, held in read.items():
            if name not in digests:
                digests[name] = digest(name, root)
            if digests[name] != held:
                found.add(module)
                break
    return found


def selected(modules: Iterable[str], record: Record | None, root: Path = ROOT) -> set[str]:
    """
    Of the modules collected, those to run: all with no record; else the ones with no entry and the changed.
    """
    wanted = set(modules)
    if record is None:
        return wanted
    moved = changed({module: read for module, read in record.items() if module in wanted}, root)
    return {module for module in wanted if module not in record or module in moved}


def kept(record: Record, ran: Mapping[str, Iterable[str]], failed: set[str], root: Path = ROOT) -> Record:
    """
    The record after a run: a module that passed keeps what it read as it is now; one with a failed test is
    forgotten, so it runs again until it passes.
    """
    after = {**record, **{module: {name: digest(name, root) for name in sorted(read)} for module, read in ran.items()}}
    return {module: read for module, read in after.items() if module not in failed}


def load(path: Path = KEPT) -> Record | None:
    try:
        kept: Record = json.loads(path.read_text(encoding='utf-8'))
    except OSError, ValueError:
        return None
    return kept


def _clear() -> None:
    for name in CACHED:
        module = sys.modules.get(name)
        for value in vars(module).values() if module is not None else ():
            clear = getattr(value, 'cache_clear', None)
            if callable(clear):
                clear()


sys.addaudithook(_audit)
_ran: Record = {}
_failed: set[str] = set()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(OPTION, action='store_true', help='Run only the modules whose data files changed.')


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption(OPTION):
        return
    keep = selected({item.nodeid.split('::')[0] for item in items}, load())
    dropped = [item for item in items if item.nodeid.split('::')[0] not in keep]
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = [item for item in items if item.nodeid.split('::')[0] in keep]


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> Any:
    module = item.nodeid.split('::')[0]
    if Reading.module != module:
        _clear()
        Reading.module, Reading.touched = module, set(_ran.get(module, {}))
    try:
        return (yield)
    finally:
        _ran[module] = dict.fromkeys(Reading.touched, '')


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.failed:
        _failed.add(report.nodeid.split('::')[0])


def pytest_sessionfinish(session: pytest.Session) -> None:
    Reading.module = None
    if not _ran:
        return
    record = kept(load() or {}, _ran, _failed)
    KEPT.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8')
