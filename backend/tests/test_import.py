from __future__ import annotations

from sqlalchemy import func, select

from app.config import PROJECT_ROOT
from app.importers.legacy_importer import run_legacy_import
from app.models import GraphEdge, Lexeme, Spelling, StudyPlan


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_legacy_import_is_idempotent(db) -> None:
    first = run_legacy_import(db, PROJECT_ROOT)
    assert first["errors"] == []
    first_lexemes = _count(db, Lexeme)
    first_edges = _count(db, GraphEdge)

    second = run_legacy_import(db, PROJECT_ROOT)
    assert second["errors"] == []
    assert _count(db, Lexeme) == first_lexemes
    assert _count(db, GraphEdge) == first_edges


def test_imported_counts(db) -> None:
    active = db.scalar(
        select(func.count()).select_from(Lexeme).where(Lexeme.status == "active")
    )
    assert active == 39
    assert _count(db, StudyPlan) >= 1

    pending = db.scalar(
        select(func.count())
        .select_from(GraphEdge)
        .where(GraphEdge.status == "pending_review")
    )
    assert pending >= 20


def test_labor_spelling_variants(db) -> None:
    lexeme = db.scalar(select(Lexeme).where(Lexeme.headword == "labor"))
    assert lexeme is not None
    spellings = {
        row.spelling: row.variant_type
        for row in db.scalars(select(Spelling).where(Spelling.lexeme_id == lexeme.id)).all()
    }
    assert spellings.get("labor") == "standard"
    assert spellings.get("labour") == "british"
    assert spellings.get("labo(u)r") == "source_form"


def test_units_keep_source_entries(db) -> None:
    from app.models import UnitWord

    assert _count(db, UnitWord) >= 39
