from __future__ import annotations

from datetime import datetime, timedelta

from app.review.fsrs import FIXED_INTERVALS, ReviewStateData, interval_days, schedule


def test_first_review_creates_state() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    nxt, interval = schedule(ReviewStateData(), "good", now)
    assert nxt.reps == 1
    assert nxt.stability > 0
    assert interval > 0
    assert nxt.due_at is not None and nxt.due_at > now


def test_again_is_shorter_than_good() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    base = ReviewStateData(stability=10.0, difficulty=5.0, reps=3, last_review_at=now - timedelta(days=5))
    again, again_interval = schedule(base, "again", now)
    good, good_interval = schedule(base, "good", now)
    assert again_interval < good_interval
    assert again.lapses == 1


def test_fixed_mode_uses_legacy_stages() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    state = ReviewStateData()
    nxt, interval = schedule(state, "good", now, mode="fixed")
    assert interval == FIXED_INTERVALS[1]
    assert nxt.fixed_stage == 1


def test_retrievability_is_monotonic() -> None:
    assert interval_days(10.0) > interval_days(1.0)
    assert interval_days(0.0) == 0.0
