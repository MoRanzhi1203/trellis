from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import StudyPlan, StudyPlanUnit, Unit  # noqa: E402

with SessionLocal() as db:
    plan = db.scalar(select(StudyPlan).where(StudyPlan.name == "12 天词汇计划"))
    print("plan", plan.id if plan else None, plan.mode if plan else None)
    for row in db.scalars(select(StudyPlanUnit).order_by(StudyPlanUnit.order_no)).all():
        unit = db.get(Unit, row.unit_id)
        print(row.plan_id, row.unit_id, row.order_no, row.planned_date, unit.title if unit else "?")
