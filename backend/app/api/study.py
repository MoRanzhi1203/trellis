from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MemoryCard, ReviewLog, StudyPlan, StudySession
from app.schemas.learning import PlanCreate, ReviewSubmit, StudySessionCreate
from app.services import reviews as review_service
from app.services import stats as stats_service

router = APIRouter(prefix="/api", tags=["study"])


@router.get("/reviews/due")
def due(limit: int = 200, db: Session = Depends(get_db)):
    return review_service.due_cards(db, limit=limit)


@router.post("/reviews/submit")
def submit(payload: ReviewSubmit, db: Session = Depends(get_db)):
    try:
        result = review_service.submit_review(
            db,
            card_id=payload.card_id,
            result=payload.result,
            difficulty_feedback=payload.difficulty_feedback,
            duration_ms=payload.duration_ms,
            client_token=payload.client_token,
            session_id=payload.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.get("/reviews/history")
def history(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.execute(
        select(ReviewLog, MemoryCard).join(MemoryCard, MemoryCard.id == ReviewLog.card_id)
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": log.id,
            "card_id": log.card_id,
            "result": log.result,
            "reviewed_at": log.reviewed_at,
            "duration_ms": log.duration_ms,
            "card_type": card.card_type,
        }
        for log, card in rows
    ]


@router.get("/study/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.scalars(select(StudyPlan).order_by(StudyPlan.id)).all()
    return [
        {
            "id": plan.id,
            "name": plan.name,
            "mode": plan.mode,
            "start_date": plan.start_date,
            "daily_target": plan.daily_target,
            "status": plan.status,
        }
        for plan in plans
    ]


@router.post("/study/plans", status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    plan = StudyPlan(
        name=payload.name,
        mode=payload.mode,
        start_date=payload.start_date or date.today(),
        daily_target=payload.daily_target,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"id": plan.id, "name": plan.name, "mode": plan.mode}


@router.post("/study/sessions", status_code=201)
def create_session(payload: StudySessionCreate, db: Session = Depends(get_db)):
    session = StudySession(
        plan_id=payload.plan_id,
        unit_id=payload.unit_id,
        kind=payload.kind,
        status="open",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "status": session.status}


@router.get("/statistics/overview")
def overview(db: Session = Depends(get_db)):
    return stats_service.overview(db)
