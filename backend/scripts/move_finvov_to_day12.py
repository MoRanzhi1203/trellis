"""Correct the fin/volv unit: it belongs to Day 12, not Day 2.

Renames and reorders the unit, and moves its plan entry to order 12. Idempotent.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Book, StudyPlan, StudyPlanUnit, Unit  # noqa: E402

DAY_BOOK = "Trellis 12 天词汇"
OLD_TITLE = "Day 2 · fin/volv 词族"
NEW_TITLE = "Day 12 · fin/volv 词族"


def main() -> None:
    with SessionLocal() as db:
        book = db.scalar(select(Book).where(Book.title == DAY_BOOK))
        if not book:
            raise SystemExit("12-day book not found")

        unit = db.scalar(select(Unit).where(Unit.book_id == book.id, Unit.title == OLD_TITLE))
        if not unit:
            unit = db.scalar(select(Unit).where(Unit.book_id == book.id, Unit.title == NEW_TITLE))
        if not unit:
            raise SystemExit("fin/volv unit not found")

        conflict = db.scalar(
            select(Unit).where(Unit.book_id == book.id, Unit.order_no == 12, Unit.id != unit.id)
        )
        if conflict:
            raise SystemExit(f"order 12 already used by unit {conflict.id}")

        unit.title = NEW_TITLE
        unit.order_no = 12
        unit.note = "fin/volv 词族 20 词（第 12 天；中间十天待补充）"

        plan = db.scalar(select(StudyPlan).where(StudyPlan.name == "12 天词汇计划"))
        if plan:
            entry = db.scalar(
                select(StudyPlanUnit).where(
                    StudyPlanUnit.plan_id == plan.id, StudyPlanUnit.unit_id == unit.id
                )
            )
            if entry:
                entry.order_no = 12
                entry.planned_date = date(2026, 11, 16)
            else:
                db.add(
                    StudyPlanUnit(
                        plan_id=plan.id,
                        unit_id=unit.id,
                        order_no=12,
                        planned_date=date(2026, 11, 16),
                    )
                )

        db.commit()
        print(f"unit {unit.id} -> {unit.title} (order {unit.order_no})")


if __name__ == "__main__":
    main()
