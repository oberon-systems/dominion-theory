# Dominion Theory

A strategy game about the rise of humanity from the first bands to states,
played through indirect control: the player is a leader who nudges a people
that decides for itself.

This is a study project with no commercial aim.

- [Why](#why)
- [How it works](#how-it-works)
- [State of the project](#state-of-the-project)
- [Quick start](#quick-start)
- [Documentation](#documentation)

## Why

Most strategy games hand the player full command of every unit. Here a band
moves, gathers and rests on its own, and the player is one voice in its
council, with a status that good and bad decisions raise and lower. The game follows that people through eras:
bands, tribes, settlements, cities, states.

## How it works

The game is a server-side simulation with thin clients. The engine advances
in ticks and is deterministic, the API is the only way in or out, and
biomes, units and eras are data. A browser client shows the game; the same
API is meant to serve other clients and programs that play, a local LLM
included.

## State of the project

Only the map generator exists: elevation and moisture noise, four biomes,
rivers, and a [pygame-ce](https://pyga.me/) window to look at the
result. Everything else is planned in [the roadmap](docs/roadmap.md).

## Quick start

Python 3.14 and `make` are required.

```bash
make install
make test
make map
```

`make map` opens a window with a generated map. A bare `make` opens a
subshell with the virtualenv active, and `make help` lists every target.

## Documentation

- [Roadmap](docs/roadmap.md) - the stages, what each builds and how.
- [Setup](docs/dev/setup.md) - install, lint, test, run.
- [Biomes](docs/biomes.md) - kinds of land and their properties.
- [Band](docs/units/band.md) - the first unit.
- [Game process](docs/game/01_bands.md) - how the band era plays.
