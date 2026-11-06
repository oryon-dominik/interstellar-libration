"""Reading a model's answer: a choice the menu allows, or a refusal that says why.

A bad answer is the normal case with a model, not an exceptional one, so :func:`read`
never raises for it. A code fence around the JSON is read through — models add one
often enough, and it carries no meaning.
"""

import json
import math
import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import NamedTuple

from .menus import Argument, Menu

_FENCE = re.compile(r"^```[A-Za-z]*\s*\n(?P<body>.*)\n\s*```$", re.DOTALL)
_KEYS = {"choice", "reason", "arguments"}


class Choice(NamedTuple):
    """An answer the menu allows: the option, its checked arguments, the model's reason."""

    option: str
    arguments: Mapping[str, object]
    reason: str


class Refusal(NamedTuple):
    """An answer the menu does not allow: what is wrong with it, and the answer as it came."""

    reason: str
    answer: str | None


def read(*, answer: str | None, menu: Menu) -> Choice | Refusal:
    """The choice in the answer, or a refusal naming the first thing that is wrong."""
    decoded = _decoded(answer)
    if isinstance(decoded, str):
        return Refusal(reason=decoded, answer=answer)
    if problem := _shape_problem(decoded):
        return Refusal(reason=problem, answer=answer)
    option = menu.option(decoded["choice"])
    if option is None:
        offered = ", ".join(each.name for each in menu.options)
        return Refusal(reason=f"choice {decoded['choice']!r} is not on the menu ({offered})", answer=answer)
    arguments = decoded["arguments"]
    if problem := _fields_problem(arguments, fields=option.arguments, where=f"option {option.name!r}", path=""):
        return Refusal(reason=problem, answer=answer)
    return Choice(option=option.name, arguments=MappingProxyType(arguments), reason=decoded["reason"])


def _decoded(answer: str | None) -> dict | str:
    """The decoded object, or the problem as text."""
    # A client hands back None when the model refused or called a tool.
    if answer is None:
        return "answer is empty"
    text = answer.strip()
    if fenced := _FENCE.match(text):
        text = fenced.group("body")
    try:
        decoded = json.loads(text)
    # ValueError covers JSONDecodeError and the digit limit of int; deep nesting raises RecursionError.
    except (ValueError, RecursionError) as error:
        return f"answer is not JSON: {error}"
    if not isinstance(decoded, dict):
        return f"answer is not an object but {type(decoded).__name__}"
    return decoded


def _shape_problem(decoded: dict) -> str:
    if missing := sorted(_KEYS - decoded.keys()):
        return f"answer lacks {', '.join(missing)}"
    if unknown := sorted(decoded.keys() - _KEYS):
        return f"answer carries unknown keys: {', '.join(unknown)}"
    if not isinstance(decoded["reason"], str) or not decoded["reason"].strip():
        return "reason is empty"
    if not isinstance(decoded["arguments"], dict):
        return "arguments is not an object"
    return ""


def _fields_problem(value: dict, *, fields: Mapping[str, Argument], where: str, path: str) -> str:
    """What is wrong with an object against its fields — the arguments of an option are one, too."""
    if missing := sorted(fields.keys() - value.keys()):
        return f"{where} lacks {', '.join(missing)}"
    if unknown := sorted(value.keys() - fields.keys()):
        return f"{where} takes no {', '.join(unknown)}"
    for name, argument in fields.items():
        if problem := _problem(value[name], argument=argument, path=f"{path}{name}"):
            return problem
    return ""


def _problem(value: object, *, argument: Argument, path: str) -> str:
    if not _fits(value, kind=argument.kind):
        return f"{path} must be {argument.kind}, got {value!r}"
    if argument.values and value not in argument.values:
        return f"{path} must be one of {', '.join(argument.values)}, got {value!r}"
    if isinstance(value, list) and argument.items is not None:
        for index, item in enumerate(value):
            if problem := _problem(item, argument=argument.items, path=f"{path}[{index}]"):
                return problem
    if isinstance(value, dict) and argument.fields:
        return _fields_problem(value, fields=argument.fields, where=path, path=f"{path}.")
    return ""


def _fits(value: object, *, kind: str) -> bool:
    # bool is a subclass of int in Python; JSON keeps them apart, and so does this check.
    # Python's decoder also reads NaN, Infinity and 1e999 as floats; JSON knows none of them.
    match kind:
        case "string":
            return isinstance(value, str)
        case "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        case "number":
            return _fits(value, kind="integer") or (isinstance(value, float) and math.isfinite(value))
        case "boolean":
            return isinstance(value, bool)
        case "array":
            return isinstance(value, list)
        case "object":
            return isinstance(value, dict)
    return False
