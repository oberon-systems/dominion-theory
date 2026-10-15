# Commands

#api #commands #stage0 #stage2

A command is what a seat asks of the game. This document says what a
command looks like, what becomes of it and which commands exist. Part of
the stage 0 design in [the roadmap](../roadmap.md).

- [What a command is](#what-a-command-is)
- [The envelope](#the-envelope)
- [The life of a command](#the-life-of-a-command)
- [Accepted and refused](#accepted-and-refused)
- [The commands](#the-commands)
- [Step mode and passing](#step-mode-and-passing)
- [Examples](#examples)
- [Open points](#open-points)

___

## What a command is

A command is the only way a player changes a game. It is part of the
game: it is written into the [run record](../architecture/records.md),
and a replay feeds the same commands back.

Pausing, changing speed and stepping are not commands. They go to the
clock, as [the protocol](protocol.md#controlling-the-clock) describes, and
leave no trace in the game.

A person, an LLM and a scripted player send the same commands in the same
form.

___

## The envelope

Every command has the same outside and its own inside.

```json
{
  "id": "c-0192",
  "kind": "vote",
  "proposal": {"kind": "move", "towards": "east"}
}
```

| Field  | Holds                                                         |
|--------|---------------------------------------------------------------|
| `id`   | chosen by the client, unique within the game                  |
| `kind` | which command this is                                         |
| others | whatever that kind needs                                      |

The seat is not in the command: it is known from who is calling. Sending
a command again with the same `id` does nothing the second time, so a
client may repeat a request it is unsure of. A command without an `id`, of
an unknown kind or with other fields than its kind takes is answered with
422 and `error-command-invalid`.

___

## The life of a command

1. **Sent.** The client posts it. The API checks its form - a known kind,
   the fields that kind needs - and answers at once.
2. **Waiting.** The runner holds it until the next step of the engine.
3. **Judged.** The engine checks it against the rules as they stand at
   that moment, and either carries it out or refuses it.
4. **Reported.** The next update carries an event that names the command
   by its `id`.
5. **Recorded.** It is written into the run record with the step it was
   judged at and what became of it.

The answer to the post therefore says only that the command was taken,
never that it worked.

```json
{"id": "c-0192", "taken": true}
```

___

## Accepted and refused

Whether a command is carried out is known only when the engine judges it:
the rules look at the state of that moment, and the state may have moved
since the client last saw it.

The verdict is an event.

```json
{"key": "command-accepted", "values": {"id": "c-0192"}}
```

```json
{"key": "command-refused", "values": {"id": "c-0192", "reason": "refused-no-council"}}
```

A reason is itself a message key, so the client shows it in the player's
language. Refusing a command costs the player nothing.

Commands of one seat are judged in the order they were sent.

___

## The commands

Two commands exist. The frame was built in stage 0 and the rules of the
council in stage 2.

| Kind   | Does                                               | Built in |
|--------|----------------------------------------------------|----------|
| `pass` | says the seat has nothing to ask this step         | stage 0  |
| `vote` | answers the council of the day with a proposal     | stage 2  |

The API checks the form of a command; the rules are the engine's, and it
judges a `vote` when the game next steps. A vote backs an option of the
table, proposes one that has no votes, or abstains with
`{"kind": "abstain"}`.

A proposal is one of two.

| Proposal          | Fields                 | In the game                           |
|-------------------|------------------------|---------------------------------------|
| `move`            | `towards`: a direction | "we go where the sun rises"           |
| `stay-and-gather` | none                   | "we stay and gather"                  |

A direction is one of eight: `north`, `north-east`, `east`, `south-east`,
`south`, `south-west`, `west`, `north-west`.

Reasons a vote may be refused, checked in this order:

| Reason                       | When                                         |
|------------------------------|----------------------------------------------|
| `refused-seat-banished`      | the player is no longer in the band          |
| `refused-no-council`         | no council sits now, or the seat is empty    |
| `refused-already-voted`      | the seat has answered this council           |
| `refused-no-such-direction`  | the band cannot go that way at all           |

The rules behind them are in
[Indirect control](../game/indirect_control.md#the-players-answer).

Two reasons belong to the frame and are built in stage 0.

| Reason                    | When                                        |
|---------------------------|---------------------------------------------|
| `refused-unknown-command` | the rules know no command of that kind, or the game has no band |
| `refused-unknown-seat`    | the game has no such seat                   |

___

## Step mode and passing

In step mode the game waits until every seat it names in `waiting` has
answered, and a seat answers by sending any command.

`pass` is the command for having nothing to say. Without it a seat that
has nothing to ask would hold the game for ever. A `pass` while a
council sits is a seat that did not vote.

In real-time mode only a council waits, for the vote or for
`DT_COUNCIL_WAIT_S` seconds. `pass` is accepted and does nothing.

___

## Examples

A seat that turns the band east at the council of the evening and passes
until the next one, in step mode. The addresses are shortened.

```text
GET  /games/7f3a9c1e/snapshot       -> seq 310, waiting ["player"], seat.council with its table
POST /games/7f3a9c1e/commands       {"id": "c-1", "kind": "vote", "proposal": {"kind": "move", "towards": "east"}}
WS   /games/7f3a9c1e/updates        <- seq 311: command-accepted c-1, council-turned
POST /games/7f3a9c1e/commands       {"id": "c-2", "kind": "pass"}
WS   /games/7f3a9c1e/updates        <- seq 312: command-accepted c-2
```

A vote at midday, when no council sits.

```text
POST /games/7f3a9c1e/commands       {"id": "c-3", "kind": "vote", "proposal": {"kind": "stay-and-gather"}}
WS   /games/7f3a9c1e/updates        <- seq 313: command-refused c-3, refused-no-council
```

___

## Open points

- **Directions by landmark** - the player speaks of the sunrise and the
  pole star, the command of compass points. A proposal that names a thing
  seen on the map, such as a river, waits for the browser client.
- **More than one command in a step** - they are judged in order, and the
  rules of the council refuse a second vote anyway. Whether a limit is
  needed is seen when there are more kinds of command.

A vote the council goes against is settled: the command is accepted, the
event `council-outvoted` follows and status falls a little, as
[Indirect control](../game/indirect_control.md#the-decision) tells.
