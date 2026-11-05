"""Attach the fin/volv family (20 words) to the 12-day plan as Day 2.

The legacy family book and unit are kept untouched; this script only creates an
additional "Day 2" unit inside the 12-day book, links the same lexemes, copies
the graph nodes/edges for the unit view, and registers the unit in the plan.
Idempotent: running it twice does not duplicate anything.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Book,
    GraphEdge,
    GraphNode,
    StudyPlan,
    StudyPlanUnit,
    Unit,
    UnitWord,
)

DAY_TITLE = "Day 2 · fin/volv 词族"
FAMILY_BOOK = "Trellis 词族词库（fin/volv）"
DAY_BOOK = "Trellis 12 天词汇"


def main() -> None:
    with SessionLocal() as db:
        day_book = db.scalar(select(Book).where(Book.title == DAY_BOOK))
        family_book = db.scalar(select(Book).where(Book.title == FAMILY_BOOK))
        if not day_book or not family_book:
            raise SystemExit("books not found; run legacy import first")

        family_unit = db.scalar(
            select(Unit).where(Unit.book_id == family_book.id).order_by(Unit.order_no)
        )
        if not family_unit:
            raise SystemExit("family unit not found")

        day2 = db.scalar(
            select(Unit).where(Unit.book_id == day_book.id, Unit.title == DAY_TITLE)
        )
        if not day2:
            day2 = Unit(
                book_id=day_book.id,
                title=DAY_TITLE,
                order_no=2,
                kind="day",
                note="fin/volv 词族 20 词（来自旧版词族词库）",
            )
            db.add(day2)
            db.flush()

        linked = 0
        for row in db.scalars(
            select(UnitWord).where(UnitWord.unit_id == family_unit.id).order_by(UnitWord.order_no)
        ).all():
            exists = db.scalar(
                select(UnitWord).where(
                    UnitWord.unit_id == day2.id, UnitWord.lexeme_id == row.lexeme_id
                )
            )
            if not exists:
                db.add(
                    UnitWord(
                        unit_id=day2.id,
                        lexeme_id=row.lexeme_id,
                        order_no=row.order_no,
                        is_new=row.is_new,
                    )
                )
                linked += 1

        # Copy graph nodes/edges so the unit view has a subgraph.
        old_nodes = db.scalars(select(GraphNode).where(GraphNode.unit_id == family_unit.id)).all()
        mapping: dict[int, int] = {}
        for node in old_nodes:
            existing = db.scalar(
                select(GraphNode).where(
                    GraphNode.node_type == node.node_type,
                    GraphNode.label == node.label,
                    GraphNode.unit_id == day2.id,
                )
            )
            if existing:
                mapping[node.id] = existing.id
                continue
            copied = GraphNode(
                node_type=node.node_type,
                label=node.label,
                lexeme_id=node.lexeme_id,
                morpheme_id=node.morpheme_id,
                unit_id=day2.id,
                meta_json=node.meta_json,
            )
            db.add(copied)
            db.flush()
            mapping[node.id] = copied.id

        copied_edges = 0
        for edge in db.scalars(
            select(GraphEdge).where(GraphEdge.source_node_id.in_(mapping.keys()))
        ).all():
            if edge.target_node_id not in mapping:
                continue
            source_id = mapping[edge.source_node_id]
            target_id = mapping[edge.target_node_id]
            exists = db.scalar(
                select(GraphEdge).where(
                    GraphEdge.source_node_id == source_id,
                    GraphEdge.target_node_id == target_id,
                    GraphEdge.relation_type == edge.relation_type,
                )
            )
            if not exists:
                db.add(
                    GraphEdge(
                        source_node_id=source_id,
                        target_node_id=target_id,
                        relation_type=edge.relation_type,
                        status=edge.status,
                        directed=edge.directed,
                        source_id=edge.source_id,
                        evidence=edge.evidence,
                        weight=edge.weight,
                    )
                )
                copied_edges += 1

        plan = db.scalar(select(StudyPlan).where(StudyPlan.name == "12 天词汇计划"))
        if plan:
            exists = db.scalar(
                select(StudyPlanUnit).where(
                    StudyPlanUnit.plan_id == plan.id, StudyPlanUnit.unit_id == day2.id
                )
            )
            if not exists:
                db.add(
                    StudyPlanUnit(
                        plan_id=plan.id,
                        unit_id=day2.id,
                        order_no=2,
                        planned_date=date(2026, 11, 6),
                    )
                )

        db.commit()
        print(
            json.dumps(
                {
                    "day2_unit_id": day2.id,
                    "linked_words": linked,
                    "graph_nodes": len(mapping),
                    "graph_edges_copied": copied_edges,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
