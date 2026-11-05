"""A compact FSRS-5 scheduler plus the legacy fixed-interval mode.

The scheduler is deterministic: it takes a review state and a rating and returns
the next state, so it can be unit-tested without a database or a UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# FSRS-5 default weights.
DEFAULT_WEIGHTS: tuple[float, ...] = (
    0.40255,
    1.18385,
    3.173,
    15.69105,
    7.1949,
    0.5345,
    1.4604,
    0.0046,
    1.54575,
    0.1192,
    1.01925,
    1.9395,
    0.11,
    0.29605,
    2.2698,
    0.2315,
    2.9898,
    0.51655,
    0.6621,
)

FACTOR = 19.0 / 81.0
DECAY = -0.5
FIXED_INTERVALS = (1, 2, 4, 7, 15)

RATING_INDEX = {"again": 1, "hard": 2, "good": 3, "easy": 4}


@dataclass
class ReviewStateData:
    stability: float = 0.0
    difficulty: float = 0.0
    reps: int = 0
    lapses: int = 0
    fixed_stage: int = 0
    due_at: datetime | None = None
    last_review_at: datetime | None = None


def retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return (1 + FACTOR * max(elapsed_days, 0.0) / stability) ** DECAY


def interval_days(stability: float, target: float = 0.9) -> float:
    if stability <= 0:
        return 0.0
    return stability / FACTOR * (target ** (1.0 / DECAY) - 1.0)


def _initial_difficulty(rating: int, weights: tuple[float, ...]) -> float:
    return min(10.0, max(1.0, weights[4] - (rating - 3) * weights[5]))


def _next_difficulty(difficulty: float, rating: int, weights: tuple[float, ...]) -> float:
    delta = -weights[6] * (rating - 3)
    damped = difficulty + delta * (10.0 - difficulty) / 9.0
    return min(10.0, max(1.0, damped))


def schedule(
    state: ReviewStateData,
    rating: str,
    now: datetime,
    mode: str = "fsrs",
    weights: tuple[float, ...] = DEFAULT_WEIGHTS,
) -> tuple[ReviewStateData, float]:
    """Return (next_state, interval_days)."""
    if mode == "fixed":
        return _schedule_fixed(state, rating, now), _fixed_interval(state, rating)

    value = RATING_INDEX[rating]
    elapsed = 0.0
    if state.last_review_at:
        elapsed = max(0.0, (now - state.last_review_at).total_seconds() / 86400.0)

    if state.stability <= 0:
        stability = weights[value - 1]
        difficulty = _initial_difficulty(value, weights)
    else:
        retrievability_now = retrievability(elapsed, state.stability)
        difficulty = _next_difficulty(state.difficulty, value, weights)
        if value == 1:
            stability = min(
                state.stability,
                weights[11]
                * max(state.difficulty, 1.0) ** (-weights[12])
                * ((state.stability + 1.0) ** weights[13] - 1.0)
                * pow(2.718281828, weights[14] * (1.0 - retrievability_now)),
            )
        else:
            growth = (
                1.0
                + pow(2.718281828, weights[8])
                * (11.0 - difficulty)
                * state.stability ** (-weights[9])
                * (pow(2.718281828, (1.0 - retrievability_now) * weights[10]) - 1.0)
            )
            if value == 2:
                growth *= weights[15]
            if value == 4:
                growth *= weights[16]
            stability = state.stability * max(growth, 0.01)
        stability = max(0.1, stability)

    interval = max(0.04, interval_days(stability, 0.9))
    due = now + timedelta(days=interval)
    next_state = ReviewStateData(
        stability=stability,
        difficulty=difficulty,
        reps=state.reps + 1,
        lapses=state.lapses + (1 if value == 1 else 0),
        fixed_stage=state.fixed_stage,
        due_at=due,
        last_review_at=now,
    )
    return next_state, interval


def _fixed_interval(state: ReviewStateData, rating: str) -> float:
    stage = state.fixed_stage
    if rating == "again":
        return FIXED_INTERVALS[0]
    if rating == "hard":
        return FIXED_INTERVALS[min(stage, len(FIXED_INTERVALS) - 1)]
    return FIXED_INTERVALS[min(stage + 1, len(FIXED_INTERVALS) - 1)]


def _schedule_fixed(state: ReviewStateData, rating: str, now: datetime) -> ReviewStateData:
    stage = state.fixed_stage
    if rating == "again":
        next_stage = 0
    elif rating == "hard":
        next_stage = stage
    else:
        next_stage = min(stage + 1, len(FIXED_INTERVALS) - 1)
    interval = _fixed_interval(state, rating)
    return ReviewStateData(
        stability=state.stability,
        difficulty=state.difficulty,
        reps=state.reps + 1,
        lapses=state.lapses + (1 if rating == "again" else 0),
        fixed_stage=next_stage,
        due_at=now + timedelta(days=interval),
        last_review_at=now,
    )
