# Localisation

#architecture #localisation #stage0

The game is played in English and Russian from the first day. This
document says how a message is made, where the words live and what keeps
the two languages complete. Part of the stage 0 design in
[the roadmap](../roadmap.md).

- [The rule](#the-rule)
- [A message](#a-message)
- [What gets a key](#what-gets-a-key)
- [Keys](#keys)
- [Catalogues](#catalogues)
- [Russian](#russian)
- [Who turns keys into words](#who-turns-keys-into-words)
- [Choosing the language](#choosing-the-language)
- [Keeping it complete](#keeping-it-complete)
- [What is not translated](#what-is-not-translated)
- [Open points](#open-points)

___

## The rule

The engine never writes a sentence. Whatever a player will read leaves the
engine as a **key** and a set of **values**, and the words are found at
the last moment, in the language of whoever is reading.

One game can therefore be watched in two languages at once, a record is
in no language at all, and changing the language re-reads the whole
history of a game in the new one.

___

## A message

A message is a key and its values.

```json
{"key": "people-lost", "values": {"unit": 4, "count": 3, "cause": "cause-bear"}}
```

A value is a number, an identifier, a date, or another key. A value that
is a key - the cause, here - is looked up in the same way and its words
put in place.

___

## What gets a key

- **Events** - everything the engine reports: a council accepted, people
  lost, a season started.
- **Names** - of biomes, resources, units, states, actions, seasons, parts
  of the day.
- **Proposals** - what the player may say to the council, in the words a
  nomad would use.
- **Refusals** - why a command was not carried out.
- **Errors of the API** that a player may see.
- **The client's own words** - buttons, labels, help.

___

## Keys

A key is lower case, words joined by hyphens, starting with the area it
belongs to.

| Area        | Example                      | Meaning                          |
|-------------|------------------------------|----------------------------------|
| `time-`     | `time-season-winter`         | name of a season                 |
| `biome-`    | `biome-forest`               | name of a biome                  |
| `unit-`     | `unit-band-state-thirst`     | name of a state of a band        |
| `council-`  | `council-turned`             | an event                         |
| `proposal-` | `proposal-move-east`         | "we go where the sun rises"      |
| `refused-`  | `refused-no-council`         | why a command was refused        |
| `error-`    | `error-game-not-found`       | an error of the API              |
| `ui-`       | `ui-pause`                   | a word of the client             |

The key of a name is built from the identifier of the thing: the biome
`forest` is `biome-forest`. Adding a biome to the
[parameters](parameters.md) therefore asks for two lines of words, one
per language, and a test says so when they are missing.

___

## Catalogues

The words are in catalogues, one directory per language and one file per
area, in the format of [Fluent](https://projectfluent.org/).

```text
i18n/locales/
  en/
    commands.ftl
    council.ftl
    errors.ftl
    people.ftl
    time.ftl
  ru/
    commands.ftl
    council.ftl
    errors.ftl
    people.ftl
    time.ftl
```

An entry names its key and gives the words, with the values in braces.

```fluent
proposal-move-east = we go where the sun rises
proposal-stay-and-gather = we stay and gather
season-started = Year { $year }: { NAME("time-season", $season) } has come.

people-lost =
    { $count ->
        [one] { $count } person has died.
       *[other] { $count } people have died.
    }
```

A value that is an identifier rather than a key is turned into a name by
the function `NAME`, which takes the area and the identifier: the season
`summer` becomes the words of `time-season-summer`.

The words of the client, the `ui-` area, live with the client; all the
rest lives with the server.

___

## Russian

Russian is the reason the format matters, and Fluent covers each case.

- **Number.** A count takes one of three forms - for 1, for 2 to 4, for 5
  and more - where English has two. The Russian entry for `people-lost`
  has three branches, `one`, `few` and `many`.
- **Case.** A name changes with its place in the sentence. A name that is
  put into other sentences is written with its forms, and the sentence
  asks for the one it needs.
- **Gender.** A verb in the past agrees with its subject. A name carries
  its gender as an attribute of its entry, and the sentence asks `NAME`
  for it with `form: "gender"` and picks the verb by the answer.

None of this is visible to the engine. It sends the same key and the same
values whatever the language.

___

## Who turns keys into words

The reader does, not the server that made the message.

- **The browser client** loads the catalogue of the player's language
  from the API and renders messages itself.
- **Any other client** does the same; the catalogues are served as they
  are, and Fluent has libraries for the common platforms.
- **The lab** renders on the Python side, to give an LLM its observation
  as text. It can give the same game to a model in either language, which
  shows whether the language changes how the model plays.
- **The console client** renders on the Python side too, with `render` of
  the `i18n` package, and prints a line per update.

The API never returns a finished sentence, with one exception: its own
log, which is in English and is not for players.

___

## Choosing the language

The language is a field of the player's profile, `en` or `ru`, and
English is the default. The API calls the field `language`; the table
keeps it in the column `locale`.

A client asks for the profile, loads that catalogue, and may change the
language at any time. Nothing in a running game changes when it does.

If a key is missing from the chosen catalogue, the English words are
shown; if they are missing too, the key itself. Both are defects that a
test should have caught, and are logged.

___

## Keeping it complete

A stage is not done while one language lacks a word. Three tests hold
this, and they run with the rest.

- **Every key in use exists in both catalogues.** The keys are gathered
  from the events and names the engine declares, from the errors the
  server raises and from the identifiers in the default parameters. Keys
  that a document states and no code declares yet are listed in the test
  by hand.
- **No catalogue holds a key nobody uses**, so dead words do not pile up.
- **Both languages take the same values.** An entry that uses `$count` in
  English uses it in Russian.

The engine does not import the catalogues, and the catalogues know
nothing of the engine. The tests are the only place the two meet.

___

## What is not translated

- Documentation, code, comments and commit messages: English.
- Logs of the server: English.
- Names of parameters and of counters, and the content of run records:
  identifiers, in no language.
- The name a player gives to a profile: shown as written.

___

## Open points

- **Numbers** - whether large numbers get separators. A date is settled:
  it is the message `time-date`, written in each catalogue.
- **The console client's own words** - its report of a replay and the
  errors of the network are in English. The `ui-` area starts with the
  browser client.
- **Who writes the Russian** - the catalogue is written by hand; a
  machine draft is only ever a draft.
- **More languages** - nothing prevents a third, and nothing is built for
  one.
