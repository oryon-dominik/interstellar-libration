"""An answer becomes a choice or a refusal with its reason — never an exception."""

import json

import pytest

from libration import answers, menus

ESCALATE = {
    "choice": "escalate",
    "reason": "The customer was charged twice.",
    "arguments": {"ticket": "TICKET-4711", "severity": 2, "team": "billing"},
}


def test_a_valid_answer_becomes_a_choice(menu):
    choice = answers.read(answer=json.dumps(ESCALATE), menu=menu)
    assert isinstance(choice, answers.Choice)
    assert choice.option == "escalate"
    assert choice.reason == "The customer was charged twice."
    assert dict(choice.arguments) == ESCALATE["arguments"]


def test_an_option_without_arguments_is_chosen_with_an_empty_object(menu):
    answer = json.dumps({"choice": "close", "reason": "Already solved.", "arguments": {}})
    assert answers.read(answer=answer, menu=menu).option == "close"


@pytest.mark.parametrize("fence", ["```json\n{}\n```", "```\n{}\n```", "  ```json\n{}\n```  \n"])
def test_a_code_fence_around_the_answer_is_read_through(menu, fence):
    answer = fence.replace("{}", json.dumps(ESCALATE))
    assert answers.read(answer=answer, menu=menu).option == "escalate"


def _with(**changes) -> str:
    """ESCALATE with top-level keys replaced; a value of None drops the key."""
    answer = {**ESCALATE, **changes}
    return json.dumps({key: value for key, value in answer.items() if value is not None})


def _arguments(**changes) -> str:
    """ESCALATE with arguments replaced; a value of None drops the argument."""
    arguments = {**ESCALATE["arguments"], **changes}
    return _with(arguments={key: value for key, value in arguments.items() if value is not None})


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ("I would escalate.", "not JSON"),
        ("[1, 2]", "not an object"),
        (_with(choice="explore"), "explore"),
        (_with(choice=None), "choice"),
        (_with(reason=None), "reason"),
        (_with(reason="  "), "reason"),
        (_with(verdict="yes"), "verdict"),
        (_with(arguments=None), "arguments"),
        (_with(arguments=["TICKET-4711"]), "arguments"),
        (_arguments(ticket=None), "ticket"),
        (_arguments(bogus=1), "bogus"),
        (_arguments(severity="2"), "severity"),
        (_arguments(severity=True), "severity"),
        (_arguments(severity=2.5), "severity"),
        (_arguments(team="legal"), "team"),
        (_arguments(ticket=7), "ticket"),
    ],
)
def test_an_answer_no_option_allows_is_refused_with_its_reason(menu, answer, reason):
    refusal = answers.read(answer=answer, menu=menu)
    assert isinstance(refusal, answers.Refusal)
    assert reason in refusal.reason
    assert refusal.answer == answer


def test_a_number_takes_integers_and_fractions_but_no_boolean():
    menu = menus.load(
        text='name = "m"\n[[option]]\nname = "a"\ndescription = "x"\n'
        '[option.arguments.share]\nkind = "number"\ndescription = "y"\n'
        '[option.arguments.sure]\nkind = "boolean"\ndescription = "z"'
    )
    for share in (1, 0.5):
        answer = json.dumps({"choice": "a", "reason": "r", "arguments": {"share": share, "sure": False}})
        assert isinstance(answers.read(answer=answer, menu=menu), answers.Choice)
    answer = json.dumps({"choice": "a", "reason": "r", "arguments": {"share": True, "sure": False}})
    assert isinstance(answers.read(answer=answer, menu=menu), answers.Refusal)


NESTED = menus.Menu(
    name="m",
    options=(
        menus.Option(
            name="a",
            description="x",
            arguments={
                "ids": menus.Argument(kind="array", description="y", items=menus.Argument("integer", "z")),
                "target": menus.Argument(
                    kind="object", description="w", fields={"team": menus.Argument("string", "v", ("billing",))}
                ),
            },
        ),
    ),
)


def _nested(**arguments) -> str:
    """An answer to NESTED with these arguments."""
    return json.dumps({"choice": "a", "reason": "r", "arguments": arguments})


def test_arrays_and_objects_are_read_through():
    choice = answers.read(answer=_nested(ids=[1, 2], target={"team": "billing"}), menu=NESTED)
    assert dict(choice.arguments) == {"ids": [1, 2], "target": {"team": "billing"}}


@pytest.mark.parametrize(
    ("arguments", "reason"),
    [
        ({"ids": 1, "target": {"team": "billing"}}, "ids must be array"),
        ({"ids": [1, "2"], "target": {"team": "billing"}}, "ids[1] must be integer"),
        ({"ids": [], "target": {"team": "support"}}, "target.team must be one of"),
        ({"ids": [], "target": {}}, "target lacks team"),
        ({"ids": [], "target": {"team": "billing", "ring": 3}}, "target takes no ring"),
        ({"ids": [], "target": "billing"}, "target must be object"),
    ],
)
def test_a_wrong_array_or_object_is_refused_with_its_path(arguments, reason):
    refusal = answers.read(answer=_nested(**arguments), menu=NESTED)
    assert isinstance(refusal, answers.Refusal)
    assert reason in refusal.reason


@pytest.mark.parametrize("answer", ["[" * 100_000, "1" * 5_000])
def test_an_answer_beyond_what_python_can_decode_is_refused(menu, answer):
    """Too deep and too long raise other errors than bad JSON does; for the caller they are one case."""
    refusal = answers.read(answer=answer, menu=menu)
    assert isinstance(refusal, answers.Refusal)
    assert "not JSON" in refusal.reason


def test_a_reply_without_content_is_refused(menu):
    """A client hands back None when the model refused or called a tool, and the quickstart passes it on."""
    refusal = answers.read(answer=None, menu=menu)
    assert isinstance(refusal, answers.Refusal)
    assert "empty" in refusal.reason
    assert refusal.answer is None


@pytest.mark.parametrize("share", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_a_number_that_is_not_finite_is_refused(share):
    """Python's decoder lets these through, and no strict schema allows them."""
    menu = menus.load(
        text='name = "m"\n[[option]]\nname = "a"\ndescription = "x"\n'
        '[option.arguments.share]\nkind = "number"\ndescription = "y"'
    )
    answer = f'{{"choice": "a", "reason": "r", "arguments": {{"share": {share}}}}}'
    assert isinstance(answers.read(answer=answer, menu=menu), answers.Refusal)
