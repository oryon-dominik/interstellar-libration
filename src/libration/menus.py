"""A menu: the closed list of options a model may choose from, read once from TOML.

A menu that no answer could ever satisfy is refused when it is read, with an exception —
that is a mistake in the menu, not in an answer. Keys libration does not know stay on the
option as ``extra``: the caller attaches what a choice sets off, libration only carries it.
"""

import re
import tomllib
from collections.abc import Mapping
from types import MappingProxyType
from typing import NamedTuple

KINDS = ("string", "integer", "number", "boolean", "array", "object")
_ARGUMENT_KEYS = {"kind", "description", "values", "items", "fields"}

# OpenAI accepts only these characters in the name of a json_schema.
_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")


class MenuError(ValueError):
    """The menu itself is wrong: no answer could ever satisfy it."""


class Argument(NamedTuple):
    """One argument of an option. An array names the kind of its items, an object its fields.

    An object without declared fields does not exist here: strict mode needs every key named.
    """

    kind: str
    description: str
    values: tuple[str, ...] = ()
    items: Argument | None = None
    fields: Mapping[str, Argument] = MappingProxyType({})


class Option(NamedTuple):
    """One thing a model may choose. ``extra`` holds the keys libration does not know."""

    name: str
    description: str
    arguments: Mapping[str, Argument] = MappingProxyType({})
    extra: Mapping[str, object] = MappingProxyType({})


class Menu(NamedTuple):
    """The closed list of options, in the order the menu declares them."""

    name: str
    options: tuple[Option, ...]

    def option(self, name: str) -> Option | None:
        """The option of that name, or None when the menu offers none."""
        return next((option for option in self.options if option.name == name), None)


def load(*, text: str) -> Menu:
    """Read a menu from TOML and refuse it when no answer could satisfy it."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise MenuError(f"menu is not TOML: {error}") from error
    name = data.get("name", "")
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise MenuError(f"menu name {name!r} must be 1-64 letters, digits, '-' or '_'")
    declared = data.get("option", [])
    if not isinstance(declared, list):
        raise MenuError(f"menu {name!r} declares its options as [[option]], a list of tables")
    options = tuple(_option(raw, menu=name) for raw in declared)
    if not options:
        raise MenuError(f"menu {name!r} offers no option")
    names = [option.name for option in options]
    if twice := sorted({each for each in names if names.count(each) > 1}):
        raise MenuError(f"menu {name!r} names an option twice: {', '.join(twice)}")
    return Menu(name=name, options=options)


def _option(declared: object, *, menu: str) -> Option:
    raw = _table(declared, where=f"an option of {menu!r}")
    name = _text(raw, key="name", where=f"an option of {menu!r}")
    description = _text(raw, key="description", where=f"option {name!r}")
    declared_arguments = _table(raw.get("arguments", {}), where=f"the arguments of option {name!r}")
    arguments = {key: _argument(value, where=f"{name}.{key}") for key, value in declared_arguments.items()}
    extra = {key: value for key, value in raw.items() if key not in ("name", "description", "arguments")}
    return Option(
        name=name,
        description=description,
        arguments=MappingProxyType(arguments),
        extra=MappingProxyType(extra),
    )


def _argument(declared: object, *, where: str) -> Argument:
    raw = _table(declared, where=f"argument {where}")
    if unknown := sorted(raw.keys() - _ARGUMENT_KEYS):
        raise MenuError(f"argument {where} takes no {', '.join(unknown)}")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise MenuError(f"argument {where} has kind {kind!r}, not one of {', '.join(KINDS)}")
    values = raw.get("values", [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise MenuError(f"argument {where}: closed values are a list of strings")
    if "values" in raw and not values:
        raise MenuError(f"argument {where} closes its values to none")
    if values and kind != "string":
        raise MenuError(f"argument {where}: closed values belong on a string argument")
    if "items" in raw and kind != "array":
        raise MenuError(f"argument {where} is no array and cannot name items")
    if "fields" in raw and kind != "object":
        raise MenuError(f"argument {where} is no object and cannot name fields")
    items = None
    if kind == "array":
        if not isinstance(raw.get("items"), dict):
            raise MenuError(f"argument {where} is an array and names no items")
        items = _argument(raw["items"], where=f"{where}[]")
    fields = {}
    if kind == "object":
        if not raw.get("fields"):
            raise MenuError(f"argument {where} is an object and names no fields")
        declared_fields = _table(raw["fields"], where=f"the fields of argument {where}")
        fields = {key: _argument(value, where=f"{where}.{key}") for key, value in declared_fields.items()}
    return Argument(
        kind=kind,
        description=_text(raw, key="description", where=f"argument {where}"),
        values=tuple(values),
        items=items,
        fields=MappingProxyType(fields),
    )


def _table(value: object, *, where: str) -> dict:
    """The TOML table at this place. Anything else in its place is a mistake in the menu."""
    if not isinstance(value, dict):
        raise MenuError(f"{where} is not a table")
    return value


def _text(raw: dict, *, key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MenuError(f"{where} has no {key}")
    return value
