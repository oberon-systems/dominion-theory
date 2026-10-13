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

Stages 0 and 1 of [the roadmap](docs/roadmap.md) are built: the frame the
game hangs on and the land. A game is created over the API, advances by
ticks through days, months and seasons, and tells its clients what
happened in English or Russian; every run is recorded and replays to the
same state. It is played in a window on a planet made from the seed, with
eleven biomes that are data, rivers, and cells that are worn out and
recover.

There is nothing to play yet. No band walks the map, and the only client
is a console one that prints the calendar. The band and the council come
in stage 2, the browser client in stage 4.

## Quick start

Python 3.14 and `make` are required.

```bash
make install
make test
make run
```

`make run` starts the server on the loopback address. In a second
terminal, watch a game: one line per update, with the date and what
happened.

```bash
make watch
```

Expected output, a line every half a second:

```text
game 7f3a9c1e
midday, day 1, month 1, year 1, spring
afternoon, day 1, month 1, year 1, spring
evening, day 1, month 1, year 1, spring
night, day 1, month 1, year 1, spring
morning, day 2, month 1, year 1, spring: Day 2 of month 1, year 1, begins.
```

`make watch WATCH='--lang ru'` prints the same in Russian. `make map`
draws the first window of a seed in a [pygame-ce](https://pyga.me/)
window or into a file, a bare `make` opens a subshell with the virtualenv
active, and `make help` lists every target.

## Documentation

- [Roadmap](docs/roadmap.md) - the stages, what each builds and how.
- [Setup](docs/dev/setup.md) - install, lint, test, run the server and
  the client, settings.
- [Architecture](docs/architecture/overview.md) - the layers, the
  packages and what one tick does.
- [Protocol](docs/api/protocol.md) - how a client talks to the game.
- [Biomes](docs/biomes/overview.md) - kinds of land and their properties.
- [Generation](docs/biomes/generation.md) - the planet, its layers, the
  rivers and the first window.
- [Band](docs/units/band.md) - the first unit.
- [Game process](docs/game/01_bands.md) - how the band era plays.
