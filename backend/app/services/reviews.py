from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lexeme, MemoryCard, ReviewLog, ReviewState, StudyEvent, StudySession
from app.review.fsrs import ReviewStateData, schedule

CARD_TYPES = ("en_to_zh",)
CARD_DIRECTION = "EN_TO_ZH"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def build_card_payload(lexeme: Lexeme) -> dict[str, tuple[str, str]]:
    """Only one card direction is allowed: English prompt -> Chinese answer."""
    lines: list[str] = []
    collocations: list[str] = []
    for sense in lexeme.senses:
        text = sense.definition_zh.strip()
        if not text:
            continue
        pos = sense.pos.strip()
        lines.append(f"{pos} {text}".strip())
        for coll in sense.collocations:
            if coll.pattern:
                collocations.append(coll.pattern)
    answer = "\n".join(lines)
    if collocations:
        answer += "\n\n常见搭配：\n" + "\n".join(collocations[:6])
    return {"en_to_zh": (lexeme.headword, answer)}


def ensure_cards_for_lexeme(db: Session, lexeme: Lexeme, mode: str = "fsrs") -> int:
    cards = build_card_payload(lexeme)
    created = 0
    now = utcnow()
    for card_type, (prompt, answer) in cards.items():
        card = db.scalar(
            select(MemoryCard).where(
                MemoryCard.lexeme_id == lexeme.id, MemoryCard.card_type == card_type
            )
        )
        if not card:
            card = MemoryCard(
                lexeme_id=lexeme.id,
                card_type=card_type,
                direction="EN_TO_ZH",
                enabled=True,
                prompt=prompt,
                answer=answer,
            )
            db.add(card)
            db.flush()
            created += 1
        else:
            card.prompt = prompt or card.prompt
            card.answer = answer or card.answer
        state = db.scalar(select(ReviewState).where(ReviewState.card_id == card.id))
        if not state:
            db.add(
                ReviewState(
                    card_id=card.id,
                    mode=mode,
                    due_at=now,
                    reps=0,
                )
            )
    db.flush()
    return created


def _state_data(state: ReviewState) -> ReviewStateData:
    return ReviewStateData(
        stability=state.stability,
        difficulty=state.difficulty,
        reps=state.reps,
        lapses=state.lapses,
        fixed_stage=state.fixed_stage,
        due_at=state.due_at,
        last_review_at=state.last_review_at,
    )


def due_cards(db: Session, now: datetime | None = None, limit: int = 200) -> list[dict]:
    now = now or utcnow()
    rows = db.execute(
        select(MemoryCard, ReviewState, Lexeme)
        .join(ReviewState, ReviewState.card_id == MemoryCard.id)
        .join(Lexeme, Lexeme.id == MemoryCard.lexeme_id)
        .where(
            ReviewState.due_at <= now,
            MemoryCard.card_type == "en_to_zh",
            MemoryCard.direction == "EN_TO_ZH",
            MemoryCard.enabled.is_(True),
        )
        .order_by(ReviewState.due_at)
        .limit(limit)
    ).all()
    return [
        {
            "card_id": card.id,
            "lexeme_id": lexeme.id,
            "headword": lexeme.headword,
            "card_type": card.card_type,
            "prompt": card.prompt,
            "answer": card.answer,
            "due_at": state.due_at,
            "mode": state.mode,
            "reps": state.reps,
            "stability": state.stability,
            "difficulty": state.difficulty,
        }
        for card, state, lexeme in rows
    ]


def submit_review(
    db: Session,
    *,
    card_id: int,
    result: str,
    difficulty_feedback: int = 3,
    duration_ms: int = 0,
    client_token: str | None = None,
    session_id: int | None = None,
) -> dict:
    if client_token:
        existing = db.scalar(select(ReviewLog).where(ReviewLog.client_token == client_token))
        if existing:
            state = db.scalar(select(ReviewState).where(ReviewState.card_id == existing.card_id))
            return {
                "card_id": existing.card_id,
                "next_due_at": state.due_at if state else None,
                "interval_days": 0.0,
                "state": json.loads(existing.next_state_json or "{}"),
                "duplicate": True,
            }

    card = db.get(MemoryCard, card_id)
    if not card:
        raise ValueError("card not found")
    state = db.scalar(select(ReviewState).where(ReviewState.card_id == card_id))
    if not state:
        state = ReviewState(card_id=card_id, mode="fsrs", due_at=utcnow())
        db.add(state)
        db.flush()

    now = utcnow()
    previous = _state_data(state)
    next_state, interval = schedule(
        previous, result, now, mode=state.mode or "fsrs"
    )

    prev_json = {
        "stability": previous.stability,
        "difficulty": previous.difficulty,
        "reps": previous.reps,
        "lapses": previous.lapses,
        "fixed_stage": previous.fixed_stage,
        "due_at": previous.due_at.isoformat() if previous.due_at else None,
    }
    next_json = {
        "stability": next_state.stability,
        "difficulty": next_state.difficulty,
        "reps": next_state.reps,
        "lapses": next_state.lapses,
        "fixed_stage": next_state.fixed_stage,
        "due_at": next_state.due_at.isoformat() if next_state.due_at else None,
    }

    state.stability = next_state.stability
    state.difficulty = next_state.difficulty
    state.reps = next_state.reps
    state.lapses = next_state.lapses
    state.fixed_stage = next_state.fixed_stage
    state.due_at = next_state.due_at
    state.last_review_at = now

    log = ReviewLog(
        card_id=card_id,
        session_id=session_id,
        result=result,
        difficulty_feedback=difficulty_feedback,
        duration_ms=duration_ms,
        prev_state_json=json.dumps(prev_json, ensure_ascii=False),
        next_state_json=json.dumps(next_json, ensure_ascii=False),
        client_token=client_token,
        reviewed_at=now,
    )
    db.add(log)
    lexeme = db.get(Lexeme, card.lexeme_id)
    db.add(
        StudyEvent(
            session_id=session_id,
            lexeme_id=card.lexeme_id,
            headword_snapshot=lexeme.headword if lexeme else "",
            event_type="review",
            result=result,
            duration_ms=duration_ms,
        )
    )
    db.commit()
    return {
        "card_id": card_id,
        "next_due_at": next_state.due_at,
        "interval_days": interval,
        "state": next_json,
    }


def ensure_session(db: Session, plan_id: int | None, unit_id: int | None, kind: str) -> StudySession:
    session = StudySession(plan_id=plan_id, unit_id=unit_id, kind=kind, status="open")
    db.add(session)
    db.flush()
    return session
