# Commands

#api #commands #stage0

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
  "kind": "call-council",
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
{"key": "command-refused", "values": {"id": "c-0192", "reason": "refused-council-too-soon"}}
```

A reason is itself a message key, so the client shows it in the player's
language. Refusing a command costs the player nothing.

Commands of one seat are judged in the order they were sent.

___

## The commands

Stage 0 builds the frame and one command. The rest are listed so that the
frame is cut to fit them; their rules are written in stage 2.

| Kind           | Does                                           | Built in |
|----------------|------------------------------------------------|----------|
| `pass`         | says the seat has nothing to ask this step     | stage 0  |
| `call-council` | gathers the band and puts a proposal to it     | stage 2  |

Until stage 2 the API checks the form of `call-council` and takes it, and
the engine refuses it with `refused-unknown-command`.

A proposal is one of three.

| Proposal          | Fields                 | In the game                           |
|-------------------|------------------------|---------------------------------------|
| `move`            | `towards`: a direction | "we go where the sun rises"           |
| `rest`            | none                   | "we rest here"                        |
| `stay-and-gather` | none                   | "we stay, we are short of food"       |

A direction is one of eight: `north`, `north-east`, `east`, `south-east`,
`south`, `south-west`, `west`, `north-west`.

Reasons a council may be refused, as they stand now:

| Reason                       | When                                         |
|------------------------------|----------------------------------------------|
| `refused-council-too-soon`   | the gap since the last council has not passed |
| `refused-no-such-direction`  | the band cannot go that way at all           |
| `refused-seat-banished`      | the player is no longer in the band          |

Two reasons belong to the frame and are built in stage 0.

| Reason                    | When                                        |
|---------------------------|---------------------------------------------|
| `refused-unknown-command` | the rules know no command of that kind      |
| `refused-unknown-seat`    | the game has no such seat                   |

___

## Step mode and passing

In step mode the game waits until every seat it names in `waiting` has
answered, and a seat answers by sending any command.

`pass` is the command for having nothing to say. Without it a seat that
does not want to call a council would hold the game for ever.

In real-time mode nothing waits. `pass` is accepted and does nothing.

___

## Examples

A seat that rests when its band is tired and passes otherwise, in step
mode. The addresses are shortened. Both examples show the council of
stage 2; the lines with `pass` are what stage 0 already answers.

```text
GET  /games/7f3a9c1e/snapshot       -> seq 311, waiting ["player"]
POST /games/7f3a9c1e/commands       {"id": "c-1", "kind": "call-council", "proposal": {"kind": "rest"}}
WS   /games/7f3a9c1e/updates        <- seq 312: command-accepted c-1, council-accepted
POST /games/7f3a9c1e/commands       {"id": "c-2", "kind": "pass"}
WS   /games/7f3a9c1e/updates        <- seq 313: command-accepted c-2
```

A council called too soon after the last one.

```text
POST /games/7f3a9c1e/commands       {"id": "c-3", "kind": "call-council", "proposal": {"kind": "move", "towards": "east"}}
WS   /games/7f3a9c1e/updates        <- seq 314: command-refused c-3, refused-council-too-soon
```

___

## Open points

- **A council the band votes down** - that is not a refused command: the
  command was carried out and the vote went against it. How it is reported
  and what it does to status is a rule of stage 2.
- **Directions by landmark** - the player speaks of the sunrise and the
  pole star, the command of compass points. Whether a proposal may also
  name a thing seen on the map, such as a river, is left for stage 2.
- **More than one command in a step** - they are judged in order, and the
  rules of the council stop a second council anyway. Whether a limit is
  needed is seen when there are more kinds of command.
