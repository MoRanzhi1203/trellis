"""Normalize all 12-day unit titles to one format: ``Day N · word / word / word``."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Book, Unit  # noqa: E402

TITLES = {
    1: "Day 1 · work / state",
    2: "Day 2 · change / social / public",
    3: "Day 3 · human / take / government",
    4: "Day 4 · accord / mean / direction",
    5: "Day 5 · paragraph / section / sheet / question",
    6: "Day 6 · increase / research / mark",
    7: "Day 7 · science / company / system / different",
    8: "Day 8 · example / found / pay / place",
    9: "Day 9 · believe / influence / data / observe",
    10: "Day 10 · form / firm",
    11: "Day 11 · interest / product / effect",
    12: "Day 12 · define / energy / fail / involve",
}


def main() -> None:
    with SessionLocal() as db:
        book = db.scalar(select(Book).where(Book.title == "Trellis 12 天词汇"))
        if not book:
            raise SystemExit("12-day book not found")
        units = db.scalars(select(Unit).where(Unit.book_id == book.id)).all()
        changed = 0
        for unit in units:
            desired = TITLES.get(unit.order_no)
            if desired and unit.title != desired:
                unit.title = desired
                changed += 1
        db.commit()
        print(f"units={len(units)} changed={changed}")
        for unit in sorted(units, key=lambda u: u.order_no):
            print(unit.order_no, unit.title)


if __name__ == "__main__":
    main()
