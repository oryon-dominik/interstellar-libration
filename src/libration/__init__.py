"""Let a language model choose from a closed list: a strict schema for the model, a checked choice for your code"""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _resolve_version() -> str:
    """Return the version pyproject.toml declares, wherever it is reachable.

    An installed package answers from its metadata — the wheel ships METADATA, never
    pyproject.toml. Only a source tree that was never installed reads the file itself.
    """
    try:
        return version("cyberise-libration")
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject.is_file():
            return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
        return "unknown"


__version__ = _resolve_version()
