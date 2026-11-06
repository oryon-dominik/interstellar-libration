"""A menu every test reads the same way: one option with arguments, one without."""

import pytest

from libration import menus

ESCALATE = """
name = "ticket-triage"

[[option]]
name = "escalate"
description = "The ticket needs a person."
route = { queue = "on-call", text = "Escalate {ticket} to {team}." }

[option.arguments.ticket]
kind = "string"
description = "The id of the ticket."

[option.arguments.severity]
kind = "integer"
description = "How urgent it is, from 1 to 5."

[option.arguments.team]
kind = "string"
description = "Which team takes it."
values = ["billing", "support"]

[[option]]
name = "close"
description = "Nothing is left to do."
"""


@pytest.fixture
def menu() -> menus.Menu:
    """The triage menu: `escalate` with three arguments, `close` with none."""
    return menus.load(text=ESCALATE)
