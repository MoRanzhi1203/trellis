"""Small, explicit helpers used by both the API and the legacy importers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dictionary import (
    Collocation,
    Example,
    Lexeme,
    LexemeTrait,
    Pronunciation,
    Sense,
    Spelling,
)


def normalize_headword(value: str) -> str:
    return " ".join(value.strip().lower().split())


def get_or_create_lexeme(
    db: Session, headword: str, kind: str = "word", source_id: int | None = None
) -> tuple[Lexeme, bool]:
    norm = normalize_headword(headword)
    existing = db.scalar(
        select(Lexeme).where(
            Lexeme.headword_norm == norm,
            Lexeme.kind == kind,
            Lexeme.status == "active",
        )
    )
    if existing:
        return existing, False
    lexeme = Lexeme(
        headword=headword.strip(),
        headword_norm=norm,
        kind=kind,
        source_id=source_id,
    )
    db.add(lexeme)
    db.flush()
    return lexeme, True


def ensure_spelling(
    db: Session,
    lexeme: Lexeme,
    spelling: str,
    variant_type: str = "standard",
    is_primary: bool = False,
) -> Spelling:
    existing = db.scalar(
        select(Spelling).where(Spelling.lexeme_id == lexeme.id, Spelling.spelling == spelling)
    )
    if existing:
        return existing
    row = Spelling(
        lexeme_id=lexeme.id,
        spelling=spelling,
        variant_type=variant_type,
        is_primary=is_primary,
    )
    db.add(row)
    db.flush()
    return row


def ensure_pronunciation(
    db: Session, lexeme: Lexeme, ipa: str, accent: str = "US", source_id: int | None = None
) -> Pronunciation | None:
    ipa = ipa.strip()
    if not ipa:
        return None
    existing = db.scalar(
        select(Pronunciation).where(
            Pronunciation.lexeme_id == lexeme.id,
            Pronunciation.ipa == ipa,
            Pronunciation.accent == accent,
        )
    )
    if existing:
        return existing
    row = Pronunciation(lexeme_id=lexeme.id, ipa=ipa, accent=accent, source_id=source_id)
    db.add(row)
    db.flush()
    return row


def ensure_sense(
    db: Session,
    lexeme: Lexeme,
    pos: str,
    definition_zh: str,
    order_no: int,
    is_primary: bool = False,
) -> Sense | None:
    definition_zh = definition_zh.strip()
    if not definition_zh:
        return None
    existing = db.scalar(
        select(Sense).where(
            Sense.lexeme_id == lexeme.id,
            Sense.pos == pos,
            Sense.definition_zh == definition_zh,
        )
    )
    if existing:
        return existing
    used = db.scalar(
        select(Sense).where(Sense.lexeme_id == lexeme.id, Sense.order_no == order_no)
    )
    if used:
        order_no = (db.scalar(select(Sense.order_no).where(Sense.lexeme_id == lexeme.id).order_by(Sense.order_no.desc())) or 0) + 1
    row = Sense(
        lexeme_id=lexeme.id,
        pos=pos,
        definition_zh=definition_zh,
        order_no=order_no,
        is_primary=is_primary,
    )
    db.add(row)
    db.flush()
    return row


def ensure_example(
    db: Session, sense: Sense, text: str, translation_zh: str = "", order_no: int = 1
) -> Example | None:
    text = text.strip()
    if not text:
        return None
    existing = db.scalar(select(Example).where(Example.sense_id == sense.id, Example.text == text))
    if existing:
        return existing
    row = Example(
        sense_id=sense.id, text=text, translation_zh=translation_zh, order_no=order_no
    )
    db.add(row)
    db.flush()
    return row


def ensure_collocation(db: Session, sense: Sense, pattern: str, note: str = "") -> Collocation | None:
    pattern = pattern.strip()
    if not pattern:
        return None
    existing = db.scalar(
        select(Collocation).where(Collocation.sense_id == sense.id, Collocation.pattern == pattern)
    )
    if existing:
        return existing
    row = Collocation(sense_id=sense.id, pattern=pattern, note=note)
    db.add(row)
    db.flush()
    return row


def ensure_trait(
    db: Session, lexeme: Lexeme, main_level: str, memory_cost: str = "", advice: str = ""
) -> LexemeTrait:
    existing = db.scalar(select(LexemeTrait).where(LexemeTrait.lexeme_id == lexeme.id))
    if existing:
        existing.main_level = main_level or existing.main_level
        existing.memory_cost = memory_cost or existing.memory_cost
        existing.advice = advice or existing.advice
        return existing
    row = LexemeTrait(
        lexeme_id=lexeme.id,
        main_level=main_level,
        memory_cost=memory_cost,
        advice=advice,
    )
    db.add(row)
    db.flush()
    return row
