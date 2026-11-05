from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.importers.legacy_importer import run_legacy_import
from app.models import Book, DataSource, Unit, UnitWord

router = APIRouter(prefix="/api", tags=["meta"])

BACKUP_DIR = settings.data_dir / "backups"


class BackupRequest(BaseModel):
    file: str


@router.get("/books")
def list_books(db: Session = Depends(get_db)):
    books = db.scalars(select(Book).order_by(Book.id)).all()
    return [
        {
            "id": book.id,
            "title": book.title,
            "description": book.description,
        }
        for book in books
    ]


@router.get("/books/{book_id}/units")
def list_units(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="book not found")
    units = db.scalars(select(Unit).where(Unit.book_id == book_id).order_by(Unit.order_no)).all()
    result = []
    for unit in units:
        count = db.scalar(
            select(func.count()).select_from(UnitWord).where(UnitWord.unit_id == unit.id)
        ) or 0
        result.append(
            {
                "id": unit.id,
                "book_id": unit.book_id,
                "title": unit.title,
                "order_no": unit.order_no,
                "kind": unit.kind,
                "note": unit.note,
                "word_count": count,
            }
        )
    return result


@router.get("/units/{unit_id}/words")
def unit_words(unit_id: int, db: Session = Depends(get_db)):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="unit not found")
    rows = db.execute(
        select(UnitWord.lexeme_id, UnitWord.order_no)
        .where(UnitWord.unit_id == unit_id)
        .order_by(UnitWord.order_no)
    ).all()
    return {"unit": unit.title, "items": [{"lexeme_id": row[0], "order_no": row[1]} for row in rows]}


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.scalars(select(DataSource).order_by(DataSource.id)).all()
    return [
        {
            "id": source.id,
            "name": source.name,
            "kind": source.kind,
            "path": source.path,
            "imported_at": source.imported_at,
        }
        for source in sources
    ]


@router.post("/imports/legacy")
def import_legacy(db: Session = Depends(get_db)):
    try:
        report = run_legacy_import(db, settings.legacy_root)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"legacy import failed: {exc}") from exc
    return report


@router.post("/backup")
def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = BACKUP_DIR / f"trellis-{stamp}.db"
    if target.exists():
        raise HTTPException(status_code=409, detail="backup file already exists")
    source = sqlite3.connect(settings.sqlite_path)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        source.close()
        destination.close()
    return {"file": target.name, "size": target.stat().st_size}


@router.post("/restore")
def restore(payload: BackupRequest):
    candidate = BACKUP_DIR / Path(payload.file).name
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="backup not found")
    with candidate.open("rb") as handle:
        header = handle.read(16)
    if not header.startswith(b"SQLite format 3\x00"):
        raise HTTPException(status_code=400, detail="not a SQLite database")
    shutil.copy2(settings.sqlite_path, BACKUP_DIR / "before-restore.db")
    source = sqlite3.connect(candidate)
    destination = sqlite3.connect(settings.sqlite_path)
    try:
        source.backup(destination)
    finally:
        source.close()
        destination.close()
    return {"ok": True, "restored": candidate.name}
