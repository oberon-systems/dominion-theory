# Dominion Theory

A strategy game about the rise of a people from the first bands to states,
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

Stages 0, 1 and 2 of [the roadmap](docs/roadmap.md) are built: the frame
the game hangs on, the land and the band. A game is created over the API,
advances by ticks through days, months and seasons, and tells its clients
what happened in English or Russian; every run is recorded and replays to
the same state. It is played in a window on a planet made from the seed,
with fifteen biomes that are data, rivers, and cells that are worn out and
recover.

A band of people one by one - born, growing up, hurt, sick and dying -
walks, gathers and camps on its own, builds a winter camp, learns skills
by living and makes the goods they open. Its council sits in the evening
when something calls it, and the player is one voice in it. The game is
played from the console; other bands come in stage 3, the browser client
in stage 4.

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

`make watch WATCH='--lang ru'` prints the same in Russian. `make play`
lets you play a band instead, on a server of its own: the same lines in
colour, a map of what the band knows and a menu to vote when its council
sits. `make live` lives a band headless for years and prints a row a
year. `make map`
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
- [Decisions](docs/game/decisions.md) - how a band decides for itself.
- [Indirect control](docs/game/indirect_control.md) - the council, the
  vote and the player's status.
- [Skills](docs/game/skills.md) - what a band learns by living and the
  goods it makes.
