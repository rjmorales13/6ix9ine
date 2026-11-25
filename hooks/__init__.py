import sys
from pathlib import Path


def command_name() -> str:
    """Use the installed binary's name when installing hooks from a build."""
    if getattr(sys, "frozen", False) and Path(sys.executable).name == "staywoke":
        return "staywoke"
    return "6ix9ine"
