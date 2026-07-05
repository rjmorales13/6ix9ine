from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

import pytest

CLI = Path.home() / ".local" / "bin" / "6ix9ine"


@pytest.fixture(scope="session")
def run_cli() -> Callable[..., dict]:
    def _run(*args: str, timeout: float = 10.0) -> dict:
        result = subprocess.run(
            [str(CLI), *args], capture_output=True, text=True, timeout=timeout, check=False
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(
                f"6ix9ine {' '.join(args)} did not return JSON "
                f"(exit={result.returncode}):\nstdout={result.stdout}\nstderr={result.stderr}"
            )

    return _run


@pytest.fixture(scope="session")
def sleep_disabled() -> Callable[[], bool]:
    def _check() -> bool:
        result = subprocess.run(["pmset", "-g"], capture_output=True, text=True, check=False)
        for line in result.stdout.splitlines():
            if "SleepDisabled" in line:
                return line.split()[-1] == "1"
        pytest.fail(f"could not find SleepDisabled in `pmset -g` output:\n{result.stdout}")

    return _check


@pytest.fixture(scope="session", autouse=True)
def require_real_environment(run_cli):
    if not CLI.exists():
        pytest.skip(f"{CLI} not found -- run ./install.sh first")
    daemon = run_cli("daemon-status")
    if not daemon.get("running"):
        pytest.skip("daemon is not running -- run `6ix9ine daemon-start` first")
    helper = run_cli("helper-status")
    if not helper.get("running"):
        pytest.skip("privileged helper is not running -- run `6ix9ine setup-privileged-helper` first")
