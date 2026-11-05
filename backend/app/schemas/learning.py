from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class BookRead(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime


class UnitRead(BaseModel):
    id: int
    book_id: int
    title: str
    order_no: int
    kind: str
    note: str
    word_count: int = 0


class PlanCreate(BaseModel):
    name: str
    mode: str = "fsrs"
    start_date: date | None = None
    daily_target: int = 20


class PlanRead(BaseModel):
    id: int
    name: str
    mode: str
    start_date: date
    daily_target: int
    status: str


class StudySessionCreate(BaseModel):
    plan_id: int | None = None
    unit_id: int | None = None
    kind: str = "review"


class StudySessionRead(BaseModel):
    id: int
    plan_id: int | None
    unit_id: int | None
    kind: str
    status: str
    started_at: datetime


class DueCardRead(BaseModel):
    card_id: int
    lexeme_id: int
    headword: str
    card_type: str
    prompt: str
    answer: str
    due_at: datetime | None
    mode: str
    reps: int
    stability: float
    difficulty: float


class ReviewSubmit(BaseModel):
    card_id: int
    result: str = Field(pattern="^(again|hard|good|easy)$")
    difficulty_feedback: int = 3
    duration_ms: int = 0
    client_token: str | None = None
    session_id: int | None = None


class ReviewSubmitResult(BaseModel):
    card_id: int
    next_due_at: datetime | None
    interval_days: float
    state: dict


class StatsOverview(BaseModel):
    total_lexemes: int
    total_cards: int
    due_today: int
    learned_today: int
    reviewed_today: int
    accuracy_today: float
    streak_days: int
    weak_words: list[dict]
