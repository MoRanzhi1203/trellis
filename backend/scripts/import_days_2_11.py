"""Import Day 2–11 word lists (from the 12-day screenshots) into the database.

Idempotent: lexemes are reused by headword, units by title, graph nodes by
(label, unit), edges by (source, target, relation_type), plan entries by
(plan, unit). Re-running merges instead of duplicating.
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
    DataSource,
    GraphEdge,
    GraphNode,
    Lexeme,
    Morpheme,
    StudyPlan,
    StudyPlanUnit,
    Unit,
    UnitWord,
)
from app.services.lexicon import (  # noqa: E402
    ensure_sense,
    ensure_spelling,
    get_or_create_lexeme,
)
from app.services.reviews import ensure_cards_for_lexeme  # noqa: E402

DATA_FILES = [
    ROOT / "backend" / "data" / "days_2_6.json",
    ROOT / "backend" / "data" / "days_7_11.json",
]


def _source(db) -> DataSource:
    source = db.scalar(select(DataSource).where(DataSource.name == "12 天词表截图"))
    if not source:
        source = DataSource(name="12 天词表截图", kind="file", path="docs/screenshots")
        db.add(source)
        db.flush()
    return source


def _book(db) -> Book:
    book = db.scalar(select(Book).where(Book.title == "Trellis 12 天词汇"))
    if not book:
        raise SystemExit("12-day book missing; run legacy import first")
    return book


def _morpheme(db, form: str, gloss: str, source) -> Morpheme:
    morpheme = db.scalar(
        select(Morpheme).where(Morpheme.form == form, Morpheme.type == "root")
    )
    if morpheme:
        if gloss and not morpheme.gloss_zh:
            morpheme.gloss_zh = gloss
        return morpheme
    morpheme = Morpheme(form=form, type="root", gloss_zh=gloss, source_id=source.id)
    db.add(morpheme)
    db.flush()
    return morpheme


def main() -> None:
    payloads = []
    for path in DATA_FILES:
        payloads.extend(json.loads(path.read_text(encoding="utf-8"))["days"])

    stats = {"units": 0, "words": 0, "senses": 0, "nodes": 0, "edges": 0, "cards": 0}

    with SessionLocal() as db:
        source = _source(db)
        book = _book(db)
        plan = db.scalar(select(StudyPlan).where(StudyPlan.name == "12 天词汇计划"))

        for day in payloads:
            unit = db.scalar(
                select(Unit).where(Unit.book_id == book.id, Unit.title == day["title"])
            )
            if not unit:
                unit = Unit(
                    book_id=book.id,
                    title=day["title"],
                    order_no=day["day"],
                    kind="day",
                    note=f"第 {day['day']} 天词表",
                )
                db.add(unit)
                db.flush()
                stats["units"] += 1

            root_nodes = {}
            for root in day["roots"]:
                morpheme = _morpheme(db, root["label"], root["gloss"], source)
                node = db.scalar(
                    select(GraphNode).where(
                        GraphNode.node_type == "root",
                        GraphNode.label == root["label"],
                        GraphNode.unit_id == unit.id,
                    )
                )
                if not node:
                    node = GraphNode(
                        node_type="root",
                        label=root["label"],
                        morpheme_id=morpheme.id,
                        unit_id=unit.id,
                        meta_json=json.dumps(
                            {"gloss": root["gloss"], "root_id": root["id"]}, ensure_ascii=False
                        ),
                    )
                    db.add(node)
                    db.flush()
                    stats["nodes"] += 1
                root_nodes[root["id"]] = node

            for order, word in enumerate(day["words"], start=1):
                lexeme, created = get_or_create_lexeme(db, word["term"], "word", source.id)
                if not created:
                    stats["words"] += 0
                ensure_spelling(db, lexeme, word["term"], "standard", True)
                if not lexeme.senses:
                    sense = ensure_sense(
                        db, lexeme, word["pos"], "；".join(word["defs"]), 1, True
                    )
                    if sense:
                        stats["senses"] += 1
                link = db.scalar(
                    select(UnitWord).where(
                        UnitWord.unit_id == unit.id, UnitWord.lexeme_id == lexeme.id
                    )
                )
                if not link:
                    db.add(
                        UnitWord(
                            unit_id=unit.id, lexeme_id=lexeme.id, order_no=order, is_new=True
                        )
                    )

                word_node = db.scalar(
                    select(GraphNode).where(
                        GraphNode.node_type == "word",
                        GraphNode.label == word["term"],
                        GraphNode.unit_id == unit.id,
                    )
                )
                if not word_node:
                    word_node = GraphNode(
                        node_type="word",
                        label=word["term"],
                        lexeme_id=lexeme.id,
                        unit_id=unit.id,
                    )
                    db.add(word_node)
                    db.flush()
                    stats["nodes"] += 1

                root_node = root_nodes.get(word["root"])
                if root_node:
                    edge = db.scalar(
                        select(GraphEdge).where(
                            GraphEdge.source_node_id == root_node.id,
                            GraphEdge.target_node_id == word_node.id,
                            GraphEdge.relation_type == "learning",
                        )
                    )
                    if not edge:
                        db.add(
                            GraphEdge(
                                source_node_id=root_node.id,
                                target_node_id=word_node.id,
                                relation_type="learning",
                                status="approved",
                                source_id=source.id,
                                evidence=f"12 天词表 Day {day['day']}",
                            )
                        )
                        stats["edges"] += 1

                ensure_cards_for_lexeme(db, lexeme, mode="fsrs")
                stats["cards"] += 1

            if plan:
                entry = db.scalar(
                    select(StudyPlanUnit).where(
                        StudyPlanUnit.plan_id == plan.id, StudyPlanUnit.unit_id == unit.id
                    )
                )
                if not entry:
                    db.add(
                        StudyPlanUnit(
                            plan_id=plan.id,
                            unit_id=unit.id,
                            order_no=day["day"],
                            planned_date=date.fromisoformat(day["date"]),
                        )
                    )

        db.commit()
        print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
