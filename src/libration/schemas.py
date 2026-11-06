"""What a model is told: the JSON schema it answers against, and the same in words.

The root is an object, because OpenAI's strict mode refuses ``anyOf`` at the root. So
``choice`` is an enum of the option names and ``arguments`` an ``anyOf`` with one object
per option; which arguments belong to which choice, :func:`libration.answers.read` checks.
"""

from collections.abc import Mapping

from .menus import Argument, Menu, Option


def schema(menu: Menu) -> dict:
    """The JSON schema an answer to this menu must match."""
    return {
        "type": "object",
        "properties": {
            "choice": {"type": "string", "enum": [option.name for option in menu.options]},
            "reason": {"type": "string"},
            "arguments": {"anyOf": [_arguments(option) for option in menu.options]},
        },
        "required": ["choice", "reason", "arguments"],
        "additionalProperties": False,
    }


def response_format(menu: Menu) -> dict:
    """The ``response_format`` field of a chat request, in strict mode."""
    return {"type": "json_schema", "json_schema": {"name": menu.name, "schema": schema(menu), "strict": True}}


def instructions(menu: Menu) -> str:
    """The part of a prompt that tells a model which options it has and how to answer."""
    lines = [
        "Answer with exactly one JSON object and nothing else:",
        '{"choice": "<an option>", "reason": "<one sentence>", "arguments": {<the arguments of that option>}}',
        "",
        "Options:",
    ]
    for option in menu.options:
        lines.append(f"- {option.name}: {option.description}")
        if not option.arguments:
            lines.append("  arguments: none, answer with {}")
        lines += _described(option.arguments, indent="  ")
    return "\n".join(lines)


def _described(arguments: Mapping[str, Argument], *, indent: str) -> list[str]:
    lines = []
    for name, argument in arguments.items():
        lines.append(f"{indent}- {name} ({_kind(argument)}): {argument.description}")
        # An array of objects declares its fields on its innermost items.
        while argument.items is not None:
            argument = argument.items
        lines += _described(argument.fields, indent=f"{indent}  ")
    return lines


def _kind(argument: Argument) -> str:
    if argument.items is not None:
        return f"array of {_kind(argument.items)}"
    if argument.values:
        return f"{argument.kind}, one of: {', '.join(argument.values)}"
    return argument.kind


def _arguments(option: Option) -> dict:
    return {
        "type": "object",
        "properties": {name: _property(argument) for name, argument in option.arguments.items()},
        "required": list(option.arguments),
        "additionalProperties": False,
    }


def _property(argument: Argument) -> dict:
    found = {"type": argument.kind, "description": argument.description}
    if argument.values:
        found["enum"] = list(argument.values)
    if argument.items is not None:
        found["items"] = _property(argument.items)
    if argument.fields:
        found["properties"] = {name: _property(field) for name, field in argument.fields.items()}
        found["required"] = list(argument.fields)
        found["additionalProperties"] = False
    return found
