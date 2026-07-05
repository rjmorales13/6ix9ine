from __future__ import annotations


def test_lid_state_reads_real_hardware(run_cli):
    status = run_cli("status")
    assert status["lid"] in ("open", "closed"), (
        f"lid state should be a real reading from ioreg, got: {status['lid']!r}"
    )
