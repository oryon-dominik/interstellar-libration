"""A menu: the closed list of options a model may choose from, read once from TOML.

A menu that no answer could ever satisfy is refused with an exception — whether it is read
by :func:`load` or built in code, the same checks run. That is a mistake in the menu, not in
an answer. Keys libration does not know stay on the
option as ``extra``: the caller attaches what a choice sets off, libration only carries it.
"""

import re
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType

KINDS = ("string", "integer", "number", "boolean", "array", "object")
_ARGUMENT_KEYS = {"kind", "description", "values", "items", "fields"}

# OpenAI accepts only these characters in the name of a json_schema.
_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")


class MenuError(ValueError):
    """The menu itself is wrong: no answer could ever satisfy it."""


@dataclass(frozen=True, slots=True)
class Argument:
    """One argument of an option. An array names the kind of its items, an object its fields.

    An object without declared fields does not exist here: strict mode needs every key named.
    """

    kind: str
    description: str
    values: tuple[str, ...] = ()
    items: Argument | None = None
    fields: Mapping[str, Argument] = MappingProxyType({})

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise MenuError(f"kind {self.kind!r} is not one of {', '.join(KINDS)}")
        if isinstance(self.values, str) or not all(isinstance(value, str) for value in self.values):
            raise MenuError("closed values are a list of strings")
        if twice := sorted({value for value in self.values if self.values.count(value) > 1}):
            raise MenuError(f"closed values name {', '.join(twice)} twice")
        if self.values and self.kind != "string":
            raise MenuError("closed values belong on a string argument")
        if self.kind == "array" and not isinstance(self.items, Argument):
            raise MenuError("an array names its items")
        if self.kind != "array" and self.items is not None:
            raise MenuError("only an array names items")
        if self.kind == "object" and not self.fields:
            raise MenuError("an object names its fields")
        if self.kind != "object" and self.fields:
            raise MenuError("only an object names fields")
        _arguments(self.fields, where="field")
        if not _filled(self.description):
            raise MenuError("the description is empty")
        object.__setattr__(self, "values", tuple(self.values))
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))


@dataclass(frozen=True, slots=True)
class Option:
    """One thing a model may choose. ``extra`` holds the keys libration does not know."""

    name: str
    description: str
    arguments: Mapping[str, Argument] = MappingProxyType({})
    extra: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        if not _filled(self.name):
            raise MenuError("an option has no name")
        if not _filled(self.description):
            raise MenuError(f"option {self.name!r} has no description")
        _arguments(self.arguments, where=f"option {self.name!r}: argument")
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True, slots=True)
class Menu:
    """The closed list of options, in the order the menu declares them."""

    name: str
    options: tuple[Option, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME.fullmatch(self.name):
            raise MenuError(f"menu name {self.name!r} must be 1-64 letters, digits, '-' or '_'")
        options = tuple(self.options)
        if not options:
            raise MenuError(f"menu {self.name!r} offers no option")
        if strays := [repr(option) for option in options if not isinstance(option, Option)]:
            raise MenuError(f"menu {self.name!r}: {', '.join(strays)} is no option")
        names = [option.name for option in options]
        if twice := sorted({each for each in names if names.count(each) > 1}):
            raise MenuError(f"menu {self.name!r} names an option twice: {', '.join(twice)}")
        object.__setattr__(self, "options", options)
        _check_strict_mode_limits(self)

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
    declared = data.get("option", [])
    if not isinstance(declared, list):
        raise MenuError(f"menu {name!r} declares its options as [[option]], a list of tables")
    return Menu(name=name, options=tuple(_option(raw, menu=name) for raw in declared))


def _option(declared: object, *, menu: str) -> Option:
    raw = _table(declared, where=f"an option of {menu!r}")
    name = raw.get("name")
    declared_arguments = _table(raw.get("arguments", {}), where=f"the arguments of option {name!r}")
    arguments = {key: _argument(value, where=f"{name}.{key}") for key, value in declared_arguments.items()}
    extra = {key: value for key, value in raw.items() if key not in ("name", "description", "arguments")}
    return Option(name=name, description=raw.get("description"), arguments=arguments, extra=extra)


def _argument(declared: object, *, where: str) -> Argument:
    """The argument a TOML table declares; MenuError names where in the menu it sits."""
    raw = _table(declared, where=f"argument {where}")
    if unknown := sorted(raw.keys() - _ARGUMENT_KEYS):
        raise MenuError(f"argument {where} takes no {', '.join(unknown)}")
    values = raw.get("values", [])
    if not isinstance(values, list):
        raise MenuError(f"argument {where}: closed values are a list of strings")
    # In code, no values means an open argument; in TOML, `values = []` is a slip.
    if "values" in raw and not values:
        raise MenuError(f"argument {where} closes its values to none")
    items = _argument(raw["items"], where=f"{where}[]") if "items" in raw else None
    declared_fields = _table(raw.get("fields", {}), where=f"the fields of argument {where}")
    fields = {key: _argument(value, where=f"{where}.{key}") for key, value in declared_fields.items()}
    try:
        return Argument(
            kind=raw.get("kind"), description=raw.get("description"), values=tuple(values), items=items, fields=fields
        )
    except MenuError as error:
        raise MenuError(f"argument {where}: {error}") from None


def _arguments(arguments: Mapping[str, Argument], *, where: str) -> None:
    """Refuse anything but a mapping of names to arguments."""
    if not isinstance(arguments, Mapping):
        raise MenuError(f"{where}s are a mapping, not {arguments!r}")
    for name, argument in arguments.items():
        if not isinstance(name, str) or not isinstance(argument, Argument):
            raise MenuError(f"{where} {name!r} is no argument but {argument!r}")


# OpenAI's documented limits for a strict schema, from "Supported schemas" in
# https://developers.openai.com/api/docs/guides/structured-outputs (read 2026-11-13).
# The guide does not say whether an array counts as a level of nesting; only objects are
# counted here, so a menu this check lets pass may still be refused for its arrays.
_MOST_PROPERTIES = 5000
_MOST_LEVELS = 10
_MOST_ENUM_VALUES = 1000
_MOST_CHARACTERS = 120_000
_MOST_LARGE_ENUM_CHARACTERS = 15_000
_LARGE_ENUM = 250
_ROOT_PROPERTIES = ("choice", "reason", "arguments")


def _check_strict_mode_limits(menu: Menu) -> None:
    """Refuse a menu whose schema strict mode would refuse, counted as libration.schemas builds it."""
    # The root object is level 1, the arguments of an option sit in an object at level 2.
    properties = [walked for option in menu.options for walked in _walked(option.arguments, level=2)]
    if (count := len(_ROOT_PROPERTIES) + len(properties)) > _MOST_PROPERTIES:
        raise MenuError(f"menu {menu.name!r} has {count} properties, strict mode allows {_MOST_PROPERTIES}")
    if (levels := max([2, *(level for _, _, level in properties)])) > _MOST_LEVELS:
        raise MenuError(f"menu {menu.name!r} nests objects {levels} levels deep, strict mode allows {_MOST_LEVELS}")
    enums = [tuple(option.name for option in menu.options)]
    enums += [values for _, argument, _ in properties if (values := _innermost(argument).values)]
    if (count := sum(map(len, enums))) > _MOST_ENUM_VALUES:
        raise MenuError(f"menu {menu.name!r} has {count} enum values, strict mode allows {_MOST_ENUM_VALUES}")
    if any(len(enum) > _LARGE_ENUM and sum(map(len, enum)) > _MOST_LARGE_ENUM_CHARACTERS for enum in enums):
        raise MenuError(
            f"menu {menu.name!r} closes an argument to more than {_LARGE_ENUM} enum values"
            f" of more than {_MOST_LARGE_ENUM_CHARACTERS} characters"
        )
    names = [*_ROOT_PROPERTIES, *(name for name, _, _ in properties), *(value for enum in enums for value in enum)]
    if (count := sum(map(len, names))) > _MOST_CHARACTERS:
        raise MenuError(
            f"menu {menu.name!r} spends {count} characters on names and enum values,"
            f" strict mode allows {_MOST_CHARACTERS}"
        )


def _walked(arguments: Mapping[str, Argument], *, level: int) -> Iterator[tuple[str, Argument, int]]:
    """Every property of an object at this level, with the level of the object holding it."""
    for name, argument in arguments.items():
        yield name, argument, level
        yield from _walked(_innermost(argument).fields, level=level + 1)


def _innermost(argument: Argument) -> Argument:
    """What an array holds at its core, through arrays of arrays; any other argument itself."""
    while argument.items is not None:
        argument = argument.items
    return argument


def _table(value: object, *, where: str) -> dict:
    """The TOML table at this place. Anything else in its place is a mistake in the menu."""
    if not isinstance(value, dict):
        raise MenuError(f"{where} is not a table")
    return value


def _filled(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
