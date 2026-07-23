# Human Simulation Tests

Real, non-mocked, end-to-end tests that drive the actual installed `6ix9ine` CLI against the
actual running daemon and the actual running root helper on this machine — exactly as a human
(or a real integrated agent) would. These are deliberately separate from `tests/unit/` (run via
`pytest tests/ -q`), which is fast, hermetic, and mock-based. These tests are slower (real `sleep`
calls), stateful (touch the real daemon's session registry and real `pmset`), and only meaningful
on a machine where 6ix9ine is actually installed and running.

## Preconditions

Before running this suite:

1. `./install.sh` has been run from the repo root (creates the venv, installs deps, sets up
   `~/.local/bin/6ix9ine` and `t69`)
2. `6ix9ine setup-privileged-helper` has been run (root helper installed and running)
3. `6ix9ine daemon-start` has been run (daemon running)

Tests that can't reach a running daemon/helper `pytest.skip()` with a clear message rather than
failing — a **skip** means "the environment isn't set up"; a **failure** means "real behavior is
wrong."

## Running

```bash
pytest human-simulation-tests/ -v
```

This is intentionally **not** part of `pyproject.toml`'s `testpaths` (`["tests"]`), so it never
runs as part of the normal fast `pytest tests/ -q` sweep, and never runs in a sandboxed/CI
environment that has no real daemon or helper to talk to.

## What's expected to happen right now (as of 2026-07-04)

- `test_session_lifecycle.py` — **should all PASS**. Verifies the real fix for bug #6
  (see `docs/planning/handoff-road-to-gummo.md`): acquire/release round-trips,
  multi-session refcounting (releasing one session while another is still held must keep sleep
  blocked), and hold-duration expiry — all checked against the real daemon and real `pmset -g`
  output.
- `test_hooks_installed.py` — **should PASS**. Verifies the real fix for bug #5: the Claude Code
  hook entries actually exist in `~/.claude/settings.json` in the real schema, and the OpenCode
  plugin file actually exists on disk.
- `test_lid_state.py` — **should PASS**. Verifies real `ioreg`-based lid-state polling returns a
  real value.
- `test_thermal_reading.py` — **should PASS** on Apple Silicon and Intel. Previously
  expected to fail (bug #4): `thermal_monitor.py` now tries `--samplers smc` (Intel) first,
  falls back to `--samplers thermal` (Apple Silicon), and maps thermal pressure level to a
  synthetic temperature. The human-simulation test confirmed the fix live on this machine:
  the helper now returns `current_temp: 40.0°C` (from "Nominal" pressure).

## How this suite has been run

1. Directly, via `pytest human-simulation-tests/ -v` from the repo root, using the same `.venv`
   that runs `tests/unit/` (no extra dependencies needed — only `subprocess`, `json`, `pathlib`,
   `pytest`).
2. Delegated to a background subagent with the same instructions and preconditions as above, as
   an independent check; its reported results were compared against the direct local run.

Both runs are expected to agree: everything green except `test_thermal_reading.py`.
