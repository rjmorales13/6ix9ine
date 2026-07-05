from __future__ import annotations


def test_thermal_current_temp_is_populated(run_cli):
    """
    KNOWN FAILING as of 2026-07-04 -- this is bug #4
    (6ix9ine-rap-sheet-docs/handoff-road-to-gummo.md), not yet fixed.

    thermal_monitor.py calls `powermetrics --samplers smc`, which errors with
    "powermetrics: unrecognized sampler: smc" on Apple Silicon (`smc` was an
    Intel-only sampler name). The daemon's thermal.current_temp therefore
    never gets populated, meaning thermal cutout protection cannot fire on
    this hardware at all. This test failing means the suite is correctly
    detecting a real, open bug -- it is not a broken test, and should not be
    "fixed" by loosening the assertion.
    """
    status = run_cli("status")
    assert status["thermal"]["current_temp"] is not None, (
        "thermal reading is broken (bug #4): powermetrics --samplers smc doesn't exist on "
        "Apple Silicon, so current_temp never gets populated. This is a known, unfixed bug -- "
        "see 6ix9ine-rap-sheet-docs/handoff-road-to-gummo.md."
    )
