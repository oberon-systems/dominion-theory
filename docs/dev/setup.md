# Setup

#dev #sop

How to bring a fresh clone to a working state, check it and run what
exists.

- [What this covers](#what-this-covers)
- [Install](#install)
- [Check](#check)
- [Run](#run)
- [Commit](#commit)
- [Clean up](#clean-up)

___

## What this covers

Everything goes through the root `Makefile`. It creates a virtualenv in
`.venv`, keeps the hook environments in `.pre-commit` inside the
repository, and holds every command in full. You need Python 3.14, `make`
and `git`.

___

## Install

Create the virtualenv, install the tooling and the game, and wire up the
git hooks.

```bash
make install
```

Open a subshell with the virtualenv active. Leave it with `exit`.

```bash
make
```

___

## Check

Run every hook over every file, tracked or not.

```bash
make lint
```

The hooks are [ruff](https://docs.astral.sh/ruff/),
[black](https://black.readthedocs.io/), [flake8](https://flake8.pycqa.org/),
[mypy](https://mypy.readthedocs.io/) and
[pymarkdown](https://pymarkdown.readthedocs.io/). ruff and black rewrite
files: when a hook reports a change, run the command again.

Run the tests.

```bash
make test
```

Expected output, with the number of tests growing over time:

```text
1 passed
```

___

## Run

Generate a map and show it in a window. Close it with Escape.

```bash
make map
```

The tool takes a size, a seed and a property to colour by. Run it from the
subshell for anything but the defaults.

```bash
python -m dominion_theory.planet.tools --width 256 --height 256 --seed 42 simple
python -m dominion_theory.planet.tools property --name food
```

___

## Commit

Commit messages are written through
[commitizen](https://commitizen-tools.github.io/commitizen/) and checked by
a hook. From the subshell:

```bash
cz commit
```

___

## Clean up

Remove the virtualenv, the hook environments and the build output.

```bash
make clean
```
