"""The README's quickstart is the first thing a reader runs, so it has to work."""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from libration import answers, menus

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def block(language: str) -> str:
    """The first fenced code block of that language."""
    return re.search(rf"```{language}\n(?P<body>.*?)```", README, re.DOTALL)["body"]


def client(reply: str) -> SimpleNamespace:
    """A chat client that answers every request with this reply."""
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: completion)))


@pytest.mark.parametrize(
    ("reply", "called"),
    [
        (block("json"), {"assign": {"ticket": "TICKET-4711", "team": "billing"}}),
        (json.dumps({"choice": "close", "reason": "Solved.", "arguments": {}}), {"close_ticket": {}}),
        ("I would escalate.", {"retry_with": {"feedback": "answer is not JSON"}}),
    ],
)
def test_the_quickstart_runs_each_branch(reply, called):
    seen = {}

    def recorder(name: str):
        return lambda **arguments: seen.update({name: arguments})

    scope = {name: recorder(name) for name in ("assign", "close_ticket", "retry_with")}
    scope |= {"client": client(reply), "menu_toml": block("toml"), "model": "any", "ticket_text": "Charged twice."}

    exec(block("python"), scope)  # noqa: S102 — the code is this repository's own README

    assert seen.keys() == called.keys()
    if "retry_with" in called:
        assert seen["retry_with"]["feedback"].startswith(called["retry_with"]["feedback"])
    else:
        assert seen == called


def test_the_argument_example_is_a_valid_argument_table():
    """The array and object example of "Writing a menu" loads once it sits under an option."""
    example = re.search(r"```toml\n(?P<body>\[option\.arguments\.tags\].*?)```", README, re.DOTALL)["body"]
    menu = menus.load(text=f'name = "m"\n[[option]]\nname = "a"\ndescription = "x"\n{example}')
    answer = json.dumps(
        {"choice": "a", "reason": "r", "arguments": {"tags": ["refund"], "customer": {"email": "a@example.com"}}}
    )
    assert isinstance(answers.read(answer=answer, menu=menu), answers.Choice)
