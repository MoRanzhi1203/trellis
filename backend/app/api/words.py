from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dictionary import LexemeCreate, LexemeRead, LexemeUpdate
from app.services import words as service

router = APIRouter(prefix="/api/words", tags=["words"])


@router.get("")
def list_words(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = None,
    kind: str | None = None,
    status: str | None = "active",
    unit_id: int | None = None,
    book_id: int | None = None,
    db: Session = Depends(get_db),
):
    total, items = service.list_words(
        db,
        offset=offset,
        limit=limit,
        q=q,
        kind=kind,
        status=status,
        unit_id=unit_id,
        book_id=book_id,
    )
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [LexemeRead.model_validate(item).model_dump() for item in items],
    }


@router.get("/search")
def search(q: str = Query(min_length=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    hits = service.search_words(db, q, limit=limit)
    return [
        LexemeRead.model_validate(item).model_dump()
        for item in hits
    ]


@router.get("/{lexeme_id}", response_model=LexemeRead)
def get_word(lexeme_id: int, db: Session = Depends(get_db)):
    lexeme = service.get_word(db, lexeme_id)
    if not lexeme:
        raise HTTPException(status_code=404, detail="word not found")
    return lexeme


@router.post("", response_model=LexemeRead, status_code=201)
def create_word(payload: LexemeCreate, db: Session = Depends(get_db)):
    try:
        lexeme = service.create_word(db, payload)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return service.get_word(db, lexeme.id)


@router.patch("/{lexeme_id}", response_model=LexemeRead)
def update_word(lexeme_id: int, payload: LexemeUpdate, db: Session = Depends(get_db)):
    lexeme = service.get_word(db, lexeme_id)
    if not lexeme:
        raise HTTPException(status_code=404, detail="word not found")
    try:
        service.update_word(db, lexeme, payload)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return service.get_word(db, lexeme_id)


@router.delete("/{lexeme_id}")
def delete_word(lexeme_id: int, hard: bool = False, db: Session = Depends(get_db)):
    lexeme = service.get_word(db, lexeme_id)
    if not lexeme:
        raise HTTPException(status_code=404, detail="word not found")
    service.delete_word(db, lexeme, hard=hard)
    return {"ok": True, "hard": hard}
