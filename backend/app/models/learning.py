from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, default="local")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("book_id", "order_no", name="uq_units_book_order"),
        CheckConstraint(
            "kind IN ('family','day','unit','custom')", name="unit_kind"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="unit")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")


class UnitWord(Base):
    __tablename__ = "unit_words"
    __table_args__ = (
        UniqueConstraint("unit_id", "lexeme_id", name="uq_unit_word"),
        CheckConstraint("order_no >= 1", name="unit_word_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (
        CheckConstraint("mode IN ('fixed','fsrs')", name="plan_mode"),
        CheckConstraint("status IN ('active','paused','finished')", name="plan_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="fsrs")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    daily_target: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class StudyPlanUnit(Base):
    __tablename__ = "study_plan_units"
    __table_args__ = (
        UniqueConstraint("plan_id", "unit_id", name="uq_plan_unit"),
        CheckConstraint("order_no >= 1", name="plan_unit_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('open','closed','abandoned')", name="session_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="review")
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")


class StudyEvent(Base):
    __tablename__ = "study_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lexeme_id: Mapped[int | None] = mapped_column(
        ForeignKey("lexemes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    headword_snapshot: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    event_type: Mapped[str] = mapped_column(String(16), nullable=False, default="learn")
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class MemoryCard(Base):
    __tablename__ = "memory_cards"
    __table_args__ = (
        UniqueConstraint("lexeme_id", "card_type", name="uq_card_lexeme_type"),
        CheckConstraint(
            "card_type IN ('en_to_zh','zh_to_en','spelling','derivation','collocation')",
            name="card_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_type: Mapped[str] = mapped_column(String(24), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="EN_TO_ZH")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ReviewState(Base):
    __tablename__ = "review_states"
    __table_args__ = (
        UniqueConstraint("card_id", name="uq_review_state_card"),
        CheckConstraint("mode IN ('fixed','fsrs')", name="state_mode"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("memory_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="fsrs")
    stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixed_stage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReviewLog(Base):
    __tablename__ = "review_logs"
    __table_args__ = (
        CheckConstraint("result IN ('again','hard','good','easy')", name="review_result"),
        UniqueConstraint("client_token", name="uq_review_client_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("memory_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    difficulty_feedback: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prev_state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    next_state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    client_token: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
