from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Lexeme, Sense, Spelling
from app.schemas.dictionary import LexemeCreate, LexemeUpdate, SpellingIn
from app.services.lexicon import normalize_headword


def _base_query():
    return select(Lexeme).options(
        selectinload(Lexeme.spellings),
        selectinload(Lexeme.pronunciations),
        selectinload(Lexeme.senses).selectinload(Sense.examples),
        selectinload(Lexeme.senses).selectinload(Sense.collocations),
        selectinload(Lexeme.etymologies),
        selectinload(Lexeme.trait),
    )


def list_words(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    q: str | None = None,
    kind: str | None = None,
    status: str | None = "active",
    unit_id: int | None = None,
    book_id: int | None = None,
) -> tuple[int, list[Lexeme]]:
    stmt = _base_query()
    count_stmt = select(func.count(Lexeme.id))
    filters = []
    if q:
        needle = f"%{q.strip()}%"
        filters.append(
            or_(
                Lexeme.headword.like(needle),
                Lexeme.id.in_(select(Spelling.lexeme_id).where(Spelling.spelling.like(needle))),
            )
        )
    if kind:
        filters.append(Lexeme.kind == kind)
    if status:
        filters.append(Lexeme.status == status)
    if unit_id:
        from app.models import UnitWord

        stmt = stmt.join(UnitWord, UnitWord.lexeme_id == Lexeme.id).where(UnitWord.unit_id == unit_id)
        count_stmt = count_stmt.join(UnitWord, UnitWord.lexeme_id == Lexeme.id).where(
            UnitWord.unit_id == unit_id
        )
    if book_id:
        from app.models import Unit, UnitWord

        stmt = stmt.join(UnitWord, UnitWord.lexeme_id == Lexeme.id).join(
            Unit, Unit.id == UnitWord.unit_id
        ).where(Unit.book_id == book_id)
        count_stmt = count_stmt.join(UnitWord, UnitWord.lexeme_id == Lexeme.id).join(
            Unit, Unit.id == UnitWord.unit_id
        ).where(Unit.book_id == book_id)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(Lexeme.headword).offset(offset).limit(limit)
    ).unique().all()
    return total, list(items)


def get_word(db: Session, lexeme_id: int) -> Lexeme | None:
    return db.scalar(_base_query().where(Lexeme.id == lexeme_id))


def _clean_sense_order(senses: list) -> None:
    used: set[int] = set()
    for index, sense in enumerate(senses, start=1):
        order = sense.order_no if sense.order_no > 0 else index
        while order in used:
            order += 1
        used.add(order)
        sense.order_no = order


def create_word(db: Session, payload: LexemeCreate) -> Lexeme:
    lexeme = Lexeme(
        headword=payload.headword.strip(),
        headword_norm=normalize_headword(payload.headword),
        kind=payload.kind,
        homograph_no=payload.homograph_no,
        source_id=None,
    )
    db.add(lexeme)
    db.flush()
    for spelling in payload.spellings or [SpellingIn(spelling=payload.headword, variant_type="standard", is_primary=True)]:
        db.add(
            Spelling(
                lexeme_id=lexeme.id,
                spelling=spelling.spelling,
                variant_type=spelling.variant_type,
                is_primary=spelling.is_primary,
            )
        )
    for pronunciation in payload.pronunciations:
        from app.models import Pronunciation

        db.add(
            Pronunciation(
                lexeme_id=lexeme.id, ipa=pronunciation.ipa, accent=pronunciation.accent
            )
        )
    _replace_senses(db, lexeme, payload.senses)
    if payload.main_level:
        from app.models import LexemeTrait

        db.add(
            LexemeTrait(
                lexeme_id=lexeme.id,
                main_level=payload.main_level,
                memory_cost=payload.memory_cost or "",
            )
        )
    db.commit()
    db.refresh(lexeme)
    return lexeme


def _replace_senses(db: Session, lexeme: Lexeme, senses) -> None:
    if not senses:
        return
    from app.models import Collocation, Example, Sense

    for old in db.scalars(select(Sense).where(Sense.lexeme_id == lexeme.id)).all():
        db.delete(old)
    db.flush()
    _clean_sense_order(senses)
    for sense in senses:
        row = Sense(
            lexeme_id=lexeme.id,
            pos=sense.pos,
            definition_zh=sense.definition_zh,
            definition_en=sense.definition_en,
            order_no=sense.order_no,
            is_primary=sense.order_no == 1,
        )
        db.add(row)
        db.flush()
        for index, example in enumerate(sense.examples, start=1):
            db.add(
                Example(
                    sense_id=row.id,
                    text=example.text,
                    translation_zh=example.translation_zh,
                    order_no=example.order_no or index,
                )
            )
        for collocation in sense.collocations:
            db.add(Collocation(sense_id=row.id, pattern=collocation.pattern, note=collocation.note))


def update_word(db: Session, lexeme: Lexeme, payload: LexemeUpdate) -> Lexeme:
    if payload.headword:
        lexeme.headword = payload.headword.strip()
        lexeme.headword_norm = normalize_headword(payload.headword)
    if payload.kind:
        lexeme.kind = payload.kind
    if payload.status:
        lexeme.status = payload.status
    if payload.spellings is not None:
        for old in db.scalars(select(Spelling).where(Spelling.lexeme_id == lexeme.id)).all():
            db.delete(old)
        db.flush()
        for spelling in payload.spellings:
            db.add(
                Spelling(
                    lexeme_id=lexeme.id,
                    spelling=spelling.spelling,
                    variant_type=spelling.variant_type,
                    is_primary=spelling.is_primary,
                )
            )
    if payload.pronunciations is not None:
        from app.models import Pronunciation

        for old in db.scalars(
            select(Pronunciation).where(Pronunciation.lexeme_id == lexeme.id)
        ).all():
            db.delete(old)
        db.flush()
        for pronunciation in payload.pronunciations:
            db.add(
                Pronunciation(
                    lexeme_id=lexeme.id, ipa=pronunciation.ipa, accent=pronunciation.accent
                )
            )
    if payload.senses is not None:
        _replace_senses(db, lexeme, payload.senses)
    if payload.main_level is not None:
        from app.models import LexemeTrait

        trait = db.scalar(select(LexemeTrait).where(LexemeTrait.lexeme_id == lexeme.id))
        if trait:
            trait.main_level = payload.main_level
            if payload.memory_cost:
                trait.memory_cost = payload.memory_cost
        else:
            db.add(
                LexemeTrait(
                    lexeme_id=lexeme.id,
                    main_level=payload.main_level,
                    memory_cost=payload.memory_cost or "",
                )
            )
    db.commit()
    db.refresh(lexeme)
    return lexeme


def delete_word(db: Session, lexeme: Lexeme, *, hard: bool = False) -> None:
    if hard:
        db.delete(lexeme)
    else:
        lexeme.status = "archived"
    db.commit()


def search_words(db: Session, q: str, limit: int = 20) -> list[Lexeme]:
    needle = f"%{q.strip()}%"
    stmt = (
        _base_query()
        .where(Lexeme.status == "active")
        .where(
            or_(
                Lexeme.headword.like(needle),
                Lexeme.id.in_(select(Spelling.lexeme_id).where(Spelling.spelling.like(needle))),
                Lexeme.id.in_(select(Sense.lexeme_id).where(Sense.definition_zh.like(needle))),
            )
        )
        .order_by(Lexeme.headword)
        .limit(limit)
    )
    return list(db.scalars(stmt).unique().all())
