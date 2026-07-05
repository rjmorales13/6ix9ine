from __future__ import annotations

from idle_tracker import IdleTracker


def test_first_observation_is_never_idle():
    tracker = IdleTracker(idle_timeout_seconds=300)
    assert tracker.observe(pid=1, cpu_percent=0.0, now=1000.0) is False


def test_pid_becomes_idle_after_timeout_with_low_cpu():
    tracker = IdleTracker(idle_timeout_seconds=300, cpu_threshold=1.0)
    tracker.observe(pid=1, cpu_percent=0.0, now=1000.0)
    assert tracker.observe(pid=1, cpu_percent=0.0, now=1000.0 + 299) is False
    assert tracker.observe(pid=1, cpu_percent=0.0, now=1000.0 + 300) is True


def test_activity_above_threshold_resets_the_idle_clock():
    tracker = IdleTracker(idle_timeout_seconds=300, cpu_threshold=1.0)
    tracker.observe(pid=1, cpu_percent=0.0, now=1000.0)
    tracker.observe(pid=1, cpu_percent=50.0, now=1000.0 + 250)
    assert tracker.observe(pid=1, cpu_percent=0.0, now=1000.0 + 300) is False


def test_tracks_multiple_pids_independently():
    tracker = IdleTracker(idle_timeout_seconds=300, cpu_threshold=1.0)
    tracker.observe(pid=1, cpu_percent=0.0, now=1000.0)
    tracker.observe(pid=2, cpu_percent=0.0, now=1200.0)

    assert tracker.observe(pid=1, cpu_percent=0.0, now=1300.0) is True
    assert tracker.observe(pid=2, cpu_percent=0.0, now=1300.0) is False


def test_forget_removes_tracked_pid():
    tracker = IdleTracker(idle_timeout_seconds=300, cpu_threshold=1.0)
    tracker.observe(pid=1, cpu_percent=0.0, now=1000.0)
    tracker.forget(1)
    assert tracker.observe(pid=1, cpu_percent=0.0, now=1000.0 + 300) is False
