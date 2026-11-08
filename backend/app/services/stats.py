from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Lexeme, MemoryCard, ReviewLog, ReviewState, StudyEvent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_start(now: datetime | None = None) -> datetime:
    current = now or _utcnow()
    return datetime.combine(current.date(), time.min)


def overview(db: Session, now: datetime | None = None) -> dict:
    current = now or _utcnow()
    start = today_start(current)

    total_lexemes = db.scalar(select(func.count()).select_from(Lexeme).where(Lexeme.status == "active")) or 0
    total_cards = db.scalar(
        select(func.count())
        .select_from(MemoryCard)
        .where(MemoryCard.enabled.is_(True), MemoryCard.direction == "EN_TO_ZH")
    ) or 0
    due_today = db.scalar(
        select(func.count())
        .select_from(ReviewState)
        .join(MemoryCard, MemoryCard.id == ReviewState.card_id)
        .where(
            ReviewState.due_at <= current,
            MemoryCard.enabled.is_(True),
            MemoryCard.direction == "EN_TO_ZH",
        )
    ) or 0
    learned_today = db.scalar(
        select(func.count())
        .select_from(StudyEvent)
        .where(StudyEvent.event_type == "learn", StudyEvent.created_at >= start)
    ) or 0
    reviewed_today = db.scalar(
        select(func.count()).select_from(ReviewLog).where(ReviewLog.reviewed_at >= start)
    ) or 0
    good_today = db.scalar(
        select(func.count())
        .select_from(ReviewLog)
        .where(ReviewLog.reviewed_at >= start, ReviewLog.result.in_(("good", "easy")))
    ) or 0
    accuracy = round(good_today / reviewed_today, 3) if reviewed_today else 0.0

    days = db.scalars(
        select(func.date(ReviewLog.reviewed_at)).where(ReviewLog.reviewed_at >= start - timedelta(days=60))
    ).all()
    day_set = {str(day) for day in days if day}
    streak = 0
    cursor = current.date()
    while str(cursor) in day_set:
        streak += 1
        cursor -= timedelta(days=1)

    weak_rows = db.execute(
        select(Lexeme.headword, func.count(ReviewLog.id).label("misses"))
        .join(MemoryCard, MemoryCard.lexeme_id == Lexeme.id)
        .join(ReviewLog, ReviewLog.card_id == MemoryCard.id)
        .where(ReviewLog.result == "again")
        .group_by(Lexeme.headword)
        .order_by(func.count(ReviewLog.id).desc())
        .limit(5)
    ).all()

    learned_lexemes = db.scalar(
        select(func.count(func.distinct(MemoryCard.lexeme_id)))
        .select_from(MemoryCard)
        .join(ReviewState, ReviewState.card_id == MemoryCard.id)
        .where(
            MemoryCard.enabled.is_(True),
            MemoryCard.direction == "EN_TO_ZH",
            ReviewState.reps > 0,
        )
    ) or 0
    mastered_lexemes = db.scalar(
        select(func.count(func.distinct(MemoryCard.lexeme_id)))
        .select_from(MemoryCard)
        .join(ReviewState, ReviewState.card_id == MemoryCard.id)
        .where(
            MemoryCard.enabled.is_(True),
            MemoryCard.direction == "EN_TO_ZH",
            ReviewState.reps >= 3,
            ReviewState.lapses <= 1,
        )
    ) or 0

    return {
        "total_lexemes": total_lexemes,
        "total_cards": total_cards,
        "due_today": due_today,
        "learned_today": learned_today,
        "reviewed_today": reviewed_today,
        "accuracy_today": accuracy,
        "streak_days": streak,
        "learned_lexemes": learned_lexemes,
        "mastered_lexemes": mastered_lexemes,
        "learning_lexemes": max(learned_lexemes - mastered_lexemes, 0),
        "weak_words": [{"headword": row[0], "misses": row[1]} for row in weak_rows],
    }
