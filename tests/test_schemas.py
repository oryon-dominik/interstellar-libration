"""The schema a model answers against, and the instructions that tell it how."""

from libration import menus, schemas


def test_the_root_is_an_object_strict_mode_accepts(menu):
    schema = schemas.schema(menu)
    assert schema["type"] == "object"
    assert schema["required"] == ["choice", "reason", "arguments"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["choice"] == {"type": "string", "enum": ["escalate", "close"]}
    assert schema["properties"]["reason"] == {"type": "string"}


def test_every_option_brings_its_own_arguments_object(menu):
    escalate, close = schemas.schema(menu)["properties"]["arguments"]["anyOf"]
    assert escalate["required"] == ["ticket", "severity", "team"]
    assert escalate["additionalProperties"] is False
    assert escalate["properties"]["severity"] == {"type": "integer", "description": "How urgent it is, from 1 to 5."}
    assert escalate["properties"]["team"]["enum"] == ["billing", "support"]
    assert close == {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def test_the_response_format_names_the_menu_and_is_strict(menu):
    response_format = schemas.response_format(menu)
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "ticket-triage"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"] == schemas.schema(menu)


def test_the_instructions_name_every_option_and_argument(menu):
    text = schemas.instructions(menu)
    for word in (
        "escalate",
        "close",
        "ticket",
        "severity",
        "team",
        "billing, support",
        '"choice"',
        '"reason"',
        '"arguments"',
    ):
        assert word in text


def test_arrays_and_objects_stay_strict():
    menu = menus.Menu(
        name="m",
        options=(
            menus.Option(
                name="a",
                description="x",
                arguments={
                    "ids": menus.Argument(kind="array", description="y", items=menus.Argument("string", "z")),
                    "target": menus.Argument(
                        kind="object", description="w", fields={"team": menus.Argument("string", "v", ("billing",))}
                    ),
                },
            ),
        ),
    )
    (arguments,) = schemas.schema(menu)["properties"]["arguments"]["anyOf"]
    assert arguments["properties"]["ids"] == {
        "type": "array",
        "description": "y",
        "items": {"type": "string", "description": "z"},
    }
    assert arguments["properties"]["target"] == {
        "type": "object",
        "description": "w",
        "properties": {"team": {"type": "string", "description": "v", "enum": ["billing"]}},
        "required": ["team"],
        "additionalProperties": False,
    }


def test_the_instructions_spell_out_items_and_fields():
    menu = menus.Menu(
        name="m",
        options=(
            menus.Option(
                name="a",
                description="x",
                arguments={
                    "ids": menus.Argument("array", "The ids.", items=menus.Argument("string", "One id.", ("a", "b"))),
                    "target": menus.Argument(
                        "object", "Where.", fields={"team": menus.Argument("string", "The team.")}
                    ),
                },
            ),
        ),
    )
    text = schemas.instructions(menu)
    assert "  - ids (array of string, one of: a, b): The ids." in text
    assert "    - team (string): The team." in text


def test_the_instructions_spell_out_the_fields_of_array_items():
    """A list of objects is only answerable when the model hears what each object holds."""
    handoff = menus.Argument("object", "One handoff.", fields={"to": menus.Argument("string", "The assignee.")})
    menu = menus.Menu(
        name="m",
        options=(
            menus.Option(
                name="a", description="x", arguments={"handoffs": menus.Argument("array", "Handoffs.", items=handoff)}
            ),
        ),
    )
    text = schemas.instructions(menu)
    assert "  - handoffs (array of object): Handoffs." in text
    assert "    - to (string): The assignee." in text
