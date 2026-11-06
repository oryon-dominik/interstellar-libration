# libration

Let a language model choose from a closed list: a strict schema for the model, a checked
choice for your code.

When a program asks a model to decide something — where a ticket goes, which step comes
next — the answer has to be one of the things the program can act on. Free text is not.
libration turns that decision into a **menu**: a small TOML file naming the options and
their arguments. From the menu it builds what the model is told, and it reads what the
model answers into exactly one of two things: a `Choice` the menu allows, or a `Refusal`
that says what is wrong.

A libration is the slow swing of a body bound to a point of balance: it moves, but it
does not get away. The answers here may wander. They do not leave the menu.

- **The list is closed.** An answer outside the menu never reaches your code as a choice.
  No fuzzy matching, no repair, no guessing.
- **A bad answer is a value, not an exception.** Models get it wrong as a matter of course,
  so `read` returns a `Refusal` with the reason, ready to send back for a retry.
- **A bad menu fails at once.** A menu no answer could satisfy raises `MenuError` when it
  is loaded, not in production on the first request.
- **Menus are data.** They live in TOML beside your code, and anything your application
  needs to attach to an option travels along with it.
- **No dependencies.** The standard library, nothing else. libration calls no model: you
  keep your client, your retries and your provider.

## Install

```shell
uv add cyberise-libration        # or: pip install cyberise-libration
```

Requires Python 3.14 or newer. The import is `libration`.

## Quickstart

Declare the decision:

```toml
name = "ticket-triage"

[[option]]
name = "escalate"
description = "The ticket needs a person."

[option.arguments.ticket]
kind = "string"
description = "The id of the ticket."

[option.arguments.team]
kind = "string"
description = "Which team takes it."
values = ["billing", "support"]

[[option]]
name = "close"
description = "Nothing is left to do."
```

Hand it to the model and read the answer. `client` is any client of the OpenAI Chat
Completions API:

```python
from libration import answers, menus, schemas

menu = menus.load(text=menu_toml)

completion = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": f"{ticket_text}\n\n{schemas.instructions(menu)}"}],
    response_format=schemas.response_format(menu),
)
reply = completion.choices[0].message.content

match answers.read(answer=reply, menu=menu):
    case answers.Choice(option="escalate", arguments=arguments):
        assign(ticket=arguments["ticket"], team=arguments["team"])
    case answers.Choice(option="close"):
        close_ticket()
    case answers.Refusal(reason=reason):
        retry_with(feedback=reason)
```

The model answers with one JSON object. `reason` is its own one-sentence justification,
kept on the `Choice`:

```json
{
  "choice": "escalate",
  "reason": "The customer was charged twice.",
  "arguments": {"ticket": "TICKET-4711", "team": "billing"}
}
```

There is no built-in "do nothing". A menu that allows skipping names an option for it, as
`close` does above.

## Why both a schema and a reader

- `schemas.response_format` asks the provider for strict structured output, so a capable
  model cannot leave the shape. The shape has a gap, though: strict mode refuses `anyOf`
  at the root, so the root is one object with `choice` as an enum and `arguments` as an
  `anyOf` of one object per option. The schema allows the arguments of one option under
  the name of another.
- `schemas.instructions` says the same in words. It matters for a model that takes no
  schema at all: send only the instructions and leave `response_format` out.
- `answers.read` closes the gap and holds the line whatever the provider did. It checks the
  choice, then every argument against the option actually chosen.

`response_format` carries the shape of the OpenAI Chat Completions API. For a provider with
a different request format, `schemas.schema` returns the bare JSON schema.

## Writing a menu

| Key | Where | Meaning |
|---|---|---|
| `name` | menu | Required. 1–64 letters, digits, `-` or `_`: it names the JSON schema |
| `[[option]]` | menu | At least one. Names are unique, the order is kept |
| `name`, `description` | option | Required. The description is what the model reads |
| `[option.arguments.<name>]` | option | Optional. Every argument is required in an answer |
| `kind` | argument | `string`, `integer`, `number`, `boolean`, `array` or `object` |
| `description` | argument | Required |
| `values` | `string` argument | Optional. Closes the argument to a list of strings |
| `items` | `array` argument | Required. An argument describing each item |
| `[….fields.<name>]` | `object` argument | Required. An argument per field |

Arrays and objects nest, and they stay strict all the way down. A free-form object does
not exist: strict mode needs every key named.

```toml
[option.arguments.tags]
kind = "array"
description = "Labels for the ticket."
items = { kind = "string", description = "One label." }

[option.arguments.customer]
kind = "object"
description = "Who wrote in."

[option.arguments.customer.fields.email]
kind = "string"
description = "Their address."
```

An argument takes only the keys above: a misspelt `value` would leave it open, so it
raises `MenuError`. Any other key on an option is yours. libration does not read it and
keeps it on `Option.extra`, which is how a choice can carry what it sets off:

```toml
[[option]]
name = "escalate"
description = "The ticket needs a person."
route = { queue = "on-call" }
```

```python
queue = menu.option(choice.option).extra["route"]["queue"]
```

## What gets refused

`answers.read` never raises for a bad answer. It returns a `Refusal` carrying the first
problem found and the answer as it came, when the answer:

- is `None`, which a client returns when the model refused or called a tool
- is not JSON, or not a JSON object — a code fence around it is read through
- lacks `choice`, `reason` or `arguments`, or carries any other key
- has an empty `reason`, or `arguments` that are not an object
- chooses something that is not on the menu
- leaves out an argument of the chosen option, or adds one it does not take
- gives an argument the wrong kind, or a value outside its `values`

The checks are JSON's, not Python's: `true` is no integer, and `NaN` and `Infinity` are no
numbers. Inside arrays and objects the reason names the path, such as `tags[1]` or
`customer.email`.

## API

| Name | What it does |
|---|---|
| `menus.load(*, text)` | Reads TOML into a `Menu`, or raises `MenuError` |
| `menus.Menu`, `Option`, `Argument` | The menu as immutable tuples, for building one in code |
| `Menu.option(name)` | The option of that name, or `None` |
| `schemas.schema(menu)` | The JSON schema of an answer |
| `schemas.response_format(menu)` | That schema as a strict `response_format` |
| `schemas.instructions(menu)` | The same in words, for the prompt |
| `answers.read(*, answer, menu)` | The reply as `Choice(option, arguments, reason)` or `Refusal(reason, answer)` |

## Development

```shell
just install   # dependencies, hooks
just test
just lint
just build     # the wheel
```

Changes are listed in [CHANGES.md](https://github.com/oryon-dominik/interstellar-libration/blob/trunk/CHANGES.md).

## Licence

[MIT](https://github.com/oryon-dominik/interstellar-libration/blob/trunk/LICENSE)
