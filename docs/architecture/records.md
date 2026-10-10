# Run records

#architecture #records #stage0

A run record is the full account of one game: enough to play it again and
enough to measure it. This document says what a record holds, how it is
written and how it is used. Part of the stage 0 design in
[the roadmap](../roadmap.md).

- [What a record is for](#what-a-record-is-for)
- [The file](#the-file)
- [Lines](#lines)
- [Counters](#counters)
- [Units in a tick](#units-in-a-tick)
- [Writing](#writing)
- [Replay](#replay)
- [The index of games](#the-index-of-games)
- [What is not in a record](#what-is-not-in-a-record)
- [Size](#size)
- [Open points](#open-points)

___

## What a record is for

Three uses, and each one sets a requirement.

- **Replay** - play a game again without the player, a person or a model,
  to debug it or to look at it. This needs the seed, the parameters and
  every command.
- **Statistics** - how long bands live, how status moves, how often each
  action is taken. This needs a row of numbers for every tick.
- **Heatmaps** - where on the map bands walk, gather, camp and die. This
  needs the place and the doing of every unit at every tick.

The lab reads records and nothing else: not the store, not the database.

___

## The file

One game, one file. It lies in the directory named by the setting
`DT_RECORDS_DIR`, under the identifier of the game.

```text
records/
  7f3a9c1e.jsonl.gz
  b02d4417.jsonl.gz
```

The file is text, one [JSON](https://www.json.org/) object per line,
compressed with gzip. Both are read by the standard library of Python and
by every tool a designer is likely to reach for.

___

## Lines

Every line has a field `t` that names its kind. A reader skips kinds it
does not know, so a new kind does not break an old reader.

| `t`       | When                    | Holds                                         |
|-----------|-------------------------|-----------------------------------------------|
| `header`  | once, first             | versions, seed, parameters, seats, columns    |
| `command` | when a command arrives  | tick, seat, the command, accepted or refused  |
| `tick`    | after every tick        | tick, clock, state hash, counters, units      |
| `event`   | when the engine reports | tick, message key, values                     |
| `footer`  | once, last              | how the game ended, last tick, final hash     |

The header carries the whole resolved tree of
[parameters](parameters.md) and its hash, the version of the engine and of
the record format, and what kind of player held each seat. A record with
no footer belongs to a game that was cut short.

```json
{"t": "header", "format": 1, "engine": "0.1.0", "game": "7f3a9c1e", "seed": 42, "params_hash": "b41f", "params": {}, "seats": [{"seat": "player", "kind": "llm"}], "counters": ["bands", "people", "born", "died", "status"], "units": ["id", "x", "y", "state", "action", "people", "food", "water"]}
{"t": "command", "tick": 12, "seat": "player", "seq": 1, "command": {"kind": "call-council", "proposal": "rest"}, "accepted": true}
{"t": "tick", "tick": 12, "parts": 12, "hash": "9d2c", "counters": [6, 94, 0, 1, 51], "units": [[1, 40, 18, "normal", "camp", 15, 22.4, 9.0]]}
{"t": "event", "tick": 12, "key": "council-accepted", "values": {"unit": 1, "proposal": "rest"}}
{"t": "footer", "outcome": "banished", "tick": 3120, "hash": "0a7e"}
```

___

## Counters

A counter is one number about the whole game at one tick. The engine
keeps them; each part of the rules declares its own.

- **The world**: bands alive, people alive, born, died by cause, cells
  exhausted.
- **The seat**: status, councils called, proposals accepted, refused,
  judged as worked, failed or disaster.

The names of the counters are listed once, in the header, and every tick
line carries the values in that order. A reader therefore needs no
knowledge of the engine that wrote the file, and a stage that adds a
counter changes no existing column.

___

## Units in a tick

Each tick line also carries one row per living unit: where it is, what
state it is in, what it did and what it holds. The columns are named in
the header, like the counters.

This is what heatmaps are drawn from. A map of where bands starve is every
row whose state is `starvation`, counted by place; a map of where they
camp is every row whose action is `camp`.

Places are planet coordinates at the scale of the era, as everywhere
else, so records of different eras can be laid over one map.

___

## Writing

The engine produces the content of the lines and the runner writes the
file; the engine itself never touches the disk.

The runner collects lines and writes them out at the end of each game
day. Each such batch is closed as a gzip member of its own, so a server
that dies loses at most the day in progress and leaves a file that still
opens.

When a game ends the runner writes the footer and marks the game as
finished in the index.

___

## Replay

A replay builds a new game from the header and feeds it the commands of
the record at the ticks they arrived.

```python
from dominion_theory.runner import replay

result = replay('records/7f3a9c1e.jsonl.gz')

result.matched         # True when every tick gave the recorded hash
result.diverged_at     # the first tick that did not, or None
result.game            # the game, at the last tick of the record
```

After every tick the state hash is compared with the one in the record.
The first tick where they differ is reported: it is either a record made
by another version of the engine, which the header shows, or a rule that
is not deterministic, which is a defect.

A model is never asked again during a replay. Its answers are already in
the record, as commands.

___

## The index of games

The database keeps one row per game, so that games can be listed and
found without opening files.

| Column        | Holds                                        |
|---------------|----------------------------------------------|
| `id`          | identifier of the game                       |
| `profile_id`  | whose game it is, as a plain value           |
| `seed`        | the seed                                     |
| `params_hash` | hash of the resolved tree                    |
| `preset`      | name of the preset, when one was used        |
| `started_at`  | wall-clock time                              |
| `finished_at` | wall-clock time, empty while running         |
| `outcome`     | how it ended, empty while running            |
| `last_tick`   | the last tick written                        |
| `record_path` | where the record lies                        |

It is a plain table with no foreign keys. The record is the truth; the
row is a pointer to it and a summary of it.

___

## What is not in a record

- **Wall-clock time, speed and pauses** - they decide nothing. The index
  holds when a game was played.
- **Who the player is** - a seat is recorded by its kind only: person,
  LLM or scripted.
- **What a model was shown and what it said** - the text of prompts and
  answers is large and is not needed to replay a game. The lab keeps it in
  a file of its own beside the record.
- **Translated text** - events are message keys with values, in any
  language at once.

___

## Size

A tick line with ten bands is about half a kilobyte before compression.
A band era of fourteen game years is seven thousand ticks: about 4 MB of
text, and well under 1 MB on disk.

A batch of a thousand such games is therefore under a gigabyte, which a
laptop holds without care.

___

## Open points

- **Snapshots inside a record** - a full state now and then would let a
  reader jump into the middle of a game, and would show how cells are
  exhausted over time. It costs size; whether it is worth it is seen once
  heatmaps are drawn.
- **Every event or some** - recording each event is simple but repeats
  what the unit rows already say for moves. Stage 2 decides which events
  are written.
- **Keeping records** - nothing removes them. Whether a batch cleans up
  after itself is a matter for the lab.
