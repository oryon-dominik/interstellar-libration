"""A menu is read from TOML once and refuses what no answer could ever satisfy."""

import pytest

from libration import menus


def test_a_menu_keeps_its_options_in_order(menu):
    assert menu.name == "ticket-triage"
    assert [option.name for option in menu.options] == ["escalate", "close"]


def test_an_argument_carries_its_kind_and_its_closed_values(menu):
    team = menu.options[0].arguments["team"]
    assert team.kind == "string"
    assert team.values == ("billing", "support")
    assert menu.options[0].arguments["severity"].values == ()


def test_an_option_without_arguments_has_none(menu):
    assert dict(menu.options[1].arguments) == {}


def test_keys_libration_does_not_know_travel_with_the_option(menu):
    route = {"queue": "on-call", "text": "Escalate {ticket} to {team}."}
    assert menu.options[0].extra == {"route": route}
    assert dict(menu.options[1].extra) == {}


ONE = ("[[option]]", 'name = "a"', 'description = "x"')


def _menu(*lines: str) -> str:
    """A menu text from its lines."""
    return "\n".join(lines)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (_menu('name = "empty"'), "no option"),
        (_menu('name = "twice"', *ONE, *ONE), "twice"),
        (_menu('name = "has space"', *ONE), "name"),
        (_menu(*ONE), "name"),
        (_menu('name = "m"', "[[option]]", 'name = "a"'), "description"),
        (_menu('name = "m"', *ONE, "[option.arguments.n]", 'kind = "float"', 'description = "y"'), "kind"),
        (_menu('name = "m"', *ONE, "[option.arguments.n]", 'kind = "integer"', 'values = ["1"]'), "values"),
    ],
)
def test_a_menu_no_answer_could_satisfy_is_refused(text, reason):
    with pytest.raises(menus.MenuError, match=reason):
        menus.load(text=text)


def test_a_menu_that_is_not_toml_is_refused():
    with pytest.raises(menus.MenuError, match="TOML"):
        menus.load(text="name = ")


NESTED = _menu(
    'name = "m"',
    *ONE,
    "[option.arguments.tickets]",
    'kind = "array"',
    'description = "The ids."',
    'items = { kind = "string", description = "One id." }',
    "[option.arguments.target]",
    'kind = "object"',
    'description = "Where."',
    "[option.arguments.target.fields.team]",
    'kind = "string"',
    'description = "The team."',
    'values = ["billing", "support"]',
)


def test_an_array_names_the_kind_of_its_items_and_an_object_its_fields():
    arguments = menus.load(text=NESTED).options[0].arguments
    assert arguments["tickets"].items == menus.Argument(kind="string", description="One id.")
    assert arguments["target"].fields["team"].values == ("billing", "support")


@pytest.mark.parametrize(
    ("argument", "reason"),
    [
        (('kind = "array"', 'description = "y"'), "items"),
        (('kind = "object"', 'description = "y"'), "fields"),
        (('kind = "array"', 'description = "y"', 'items = { kind = "float", description = "z" }'), "kind"),
    ],
)
def test_an_array_without_items_or_an_object_without_fields_is_refused(argument, reason):
    with pytest.raises(menus.MenuError, match=reason):
        menus.load(text=_menu('name = "m"', *ONE, "[option.arguments.n]", *argument))


OPTION = (*ONE, "[option.arguments.n]")
STRING = ('kind = "string"', 'description = "y"')


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (_menu('name = "m"', 'option = "a"'), "option"),
        (_menu('name = "m"', "option = [1]"), "option"),
        (_menu('name = "m"', "[option]", 'name = "a"', 'description = "x"'), "option"),
        (_menu('name = "m"', *ONE, 'arguments = "n"'), "arguments"),
        (_menu('name = "m"', *ONE, "[option.arguments]", 'n = "string"'), "n"),
        (_menu('name = "m"', *OPTION, 'kind = "object"', 'description = "y"', 'fields = "f"'), "n"),
        (
            _menu(
                'name = "m"', *OPTION, 'kind = "object"', 'description = "y"', "[option.arguments.n.fields]", "f = 1"
            ),
            "f",
        ),
        (_menu('name = "m"', *OPTION, *STRING, 'values = "abc"'), "values"),
        (_menu('name = "m"', *OPTION, *STRING, "values = 5"), "values"),
        (_menu('name = "m"', *OPTION, *STRING, "values = []"), "values"),
        (_menu('name = "m"', *OPTION, *STRING, 'items = { kind = "string", description = "z" }'), "items"),
        (_menu('name = "m"', *OPTION, *STRING, "[option.arguments.n.fields.f]", *STRING), "fields"),
    ],
)
def test_a_malformed_menu_is_refused_with_a_menu_error(text, reason):
    """Every mistake in a menu reaches the caller as MenuError, whatever shape the TOML took."""
    with pytest.raises(menus.MenuError, match=reason):
        menus.load(text=text)


@pytest.mark.parametrize("key", ["value", "enum", "kinds"])
def test_a_misspelt_key_on_an_argument_is_refused(key):
    """Read past, `value = ["a"]` would leave an argument open that the author meant to close."""
    with pytest.raises(menus.MenuError, match=key):
        menus.load(text=_menu('name = "m"', *OPTION, *STRING, f'{key} = ["a"]'))


def test_a_menu_name_with_a_trailing_newline_is_refused():
    """OpenAI refuses such a name at request time; the menu is the place to say so."""
    with pytest.raises(menus.MenuError, match="name"):
        menus.load(text=_menu(r'name = "m\n"', *ONE))
