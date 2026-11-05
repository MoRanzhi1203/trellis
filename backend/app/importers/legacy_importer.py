"""Idempotent migration of the legacy Trellis data into the relational schema.

Guiding rules:
- never modify or delete a legacy file;
- every write is ``get_or_create`` keyed by a stable natural key;
- re-running the import merges missing fields instead of duplicating rows;
- etymology and derivation claims are imported as ``pending_review``;
- every generated row keeps its ``data_source``.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.legacy_parser import (
    parse_legacy_graph,
    parse_markdown,
    parse_words_js,
    parse_workbook,
)
from app.models import (
    Book,
    DataSource,
    Etymology,
    GraphEdge,
    GraphNode,
    Lexeme,
    LexemeMorpheme,
    LexemeTrait,
    Morpheme,
    Sense,
    SenseContrastGroup,
    SenseContrastItem,
    Spelling,
    StudyPlan,
    StudyPlanUnit,
    Unit,
    UnitWord,
)
from app.services.lexicon import (
    ensure_collocation,
    ensure_example,
    ensure_pronunciation,
    ensure_sense,
    ensure_spelling,
    ensure_trait,
    get_or_create_lexeme,
)


class Report:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.errors: list[str] = []
        self.notes: list[str] = []

    def add(self, key: str, value: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + value

    def as_dict(self) -> dict:
        return {"counts": self.counts, "errors": self.errors, "notes": self.notes}


def _clean_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _canonical_headword(value: str) -> str:
    """``labo(u)r`` -> ``labor`` while keeping the source form as a spelling."""
    return value.replace("(u)", "").strip()


def _add_spelling_variants(db: Session, lexeme: Lexeme, source_form: str) -> None:
    standard = source_form.replace("(u)", "")
    british = source_form.replace("(u)", "u")
    if standard == source_form:
        return
    for spelling, variant in (
        (standard, "standard"),
        (british, "british"),
        (source_form, "source_form"),
    ):
        ensure_spelling(db, lexeme, spelling, variant, spelling == standard)


def _split_semicolon(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"[；;]", value) if part.strip()]


def _source(db: Session, name: str, kind: str, path: str) -> DataSource:
    existing = db.scalar(select(DataSource).where(DataSource.name == name))
    if existing:
        return existing
    row = DataSource(name=name, kind=kind, path=path)
    db.add(row)
    db.flush()
    return row


def _book(db: Session, title: str, description: str = "") -> Book:
    existing = db.scalar(select(Book).where(Book.title == title))
    if existing:
        return existing
    row = Book(title=title, description=description)
    db.add(row)
    db.flush()
    return row


def _unit(db: Session, book: Book, title: str, order_no: int, kind: str) -> Unit:
    existing = db.scalar(select(Unit).where(Unit.book_id == book.id, Unit.title == title))
    if existing:
        return existing
    row = Unit(book_id=book.id, title=title, order_no=order_no, kind=kind)
    db.add(row)
    db.flush()
    return row


def _unit_word(db: Session, unit: Unit, lexeme: Lexeme, order_no: int) -> None:
    existing = db.scalar(
        select(UnitWord).where(UnitWord.unit_id == unit.id, UnitWord.lexeme_id == lexeme.id)
    )
    if existing:
        return
    db.add(UnitWord(unit_id=unit.id, lexeme_id=lexeme.id, order_no=order_no))


def _graph_node(
    db: Session,
    node_type: str,
    label: str,
    *,
    unit: Unit | None = None,
    lexeme: Lexeme | None = None,
    morpheme: Morpheme | None = None,
    meta: dict | None = None,
) -> GraphNode:
    existing = db.scalar(
        select(GraphNode).where(
            GraphNode.node_type == node_type,
            GraphNode.label == label,
            GraphNode.unit_id == (unit.id if unit else None),
        )
    )
    if existing:
        if lexeme and not existing.lexeme_id:
            existing.lexeme_id = lexeme.id
        if morpheme and not existing.morpheme_id:
            existing.morpheme_id = morpheme.id
        return existing
    row = GraphNode(
        node_type=node_type,
        label=label,
        unit_id=unit.id if unit else None,
        lexeme_id=lexeme.id if lexeme else None,
        morpheme_id=morpheme.id if morpheme else None,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return row


def _edge(
    db: Session,
    source_node: GraphNode,
    target_node: GraphNode,
    relation_type: str,
    status: str,
    data_source: DataSource,
    evidence: str = "",
) -> GraphEdge | None:
    existing = db.scalar(
        select(GraphEdge).where(
            GraphEdge.source_node_id == source_node.id,
            GraphEdge.target_node_id == target_node.id,
            GraphEdge.relation_type == relation_type,
        )
    )
    if existing:
        return existing
    row = GraphEdge(
        source_node_id=source_node.id,
        target_node_id=target_node.id,
        relation_type=relation_type,
        status=status,
        source_id=data_source.id,
        evidence=evidence,
    )
    db.add(row)
    db.flush()
    return row


def _morpheme(db: Session, form: str, kind: str, gloss: str, source: DataSource) -> Morpheme:
    form = form.strip()
    existing = db.scalar(select(Morpheme).where(Morpheme.form == form, Morpheme.type == kind))
    if existing:
        if gloss and not existing.gloss_zh:
            existing.gloss_zh = gloss
        return existing
    row = Morpheme(form=form, type=kind, gloss_zh=gloss, source_id=source.id)
    db.add(row)
    db.flush()
    return row


def _link_morpheme(
    db: Session, lexeme: Lexeme, morpheme: Morpheme, role: str, position: int
) -> None:
    existing = db.scalar(
        select(LexemeMorpheme).where(
            LexemeMorpheme.lexeme_id == lexeme.id,
            LexemeMorpheme.morpheme_id == morpheme.id,
            LexemeMorpheme.role == role,
        )
    )
    if existing:
        return
    db.add(
        LexemeMorpheme(
            lexeme_id=lexeme.id, morpheme_id=morpheme.id, role=role, position=position
        )
    )


def _pending_etymology(
    db: Session, lexeme: Lexeme, description: str, source: DataSource, evidence: str
) -> None:
    existing = db.scalar(
        select(Etymology).where(
            Etymology.lexeme_id == lexeme.id, Etymology.description_zh == description
        )
    )
    if existing:
        return
    db.add(
        Etymology(
            lexeme_id=lexeme.id,
            description_zh=description,
            confidence="medium",
            status="pending_review",
            evidence=evidence,
            source_id=source.id,
        )
    )


def import_words_js(db: Session, path: Path, report: Report) -> None:
    data = parse_words_js(path)
    source = _source(db, "legacy:data/words.js", "legacy", str(path))
    book = _book(db, "Trellis 12 天词汇", "从旧版 words.js 迁移的 12 天学习单元")

    for day in data.get("days", []):
        unit = _unit(db, book, f"Day {day['day']}", order_no=day["day"], kind="day")
        word_nodes: dict[str, GraphNode] = {}
        order = 0
        for group in day.get("groups", []):
            for word in group.get("words", []):
                order += 1
                raw_term = word["term"]
                term = _canonical_headword(raw_term)
                lexeme, created = get_or_create_lexeme(
                    db, term, word.get("kind", "word"), source.id
                )
                report.add("lexemes_created" if created else "lexemes_merged")
                ensure_spelling(db, lexeme, term, "standard", True)
                if term != raw_term:
                    _add_spelling_variants(db, lexeme, raw_term)
                for index, sense in enumerate(word.get("senses", []), start=1):
                    meanings = sense.get("meanings", [])
                    definition = "；".join(meanings) if isinstance(meanings, list) else str(meanings)
                    result = ensure_sense(
                        db, lexeme, sense.get("pos", ""), definition, index, index == 1
                    )
                    if result:
                        report.add("senses")
                if word.get("main"):
                    ensure_trait(db, lexeme, "主词")
                _unit_word(db, unit, lexeme, order)
                word_nodes[word["id"]] = _graph_node(
                    db, "word", word["term"], unit=unit, lexeme=lexeme
                )
                report.add("graph_nodes")

        graph = day.get("graph") or {}
        root_nodes: dict[str, GraphNode] = {}
        for root in graph.get("roots", []):
            morpheme = _morpheme(db, root["label"], "root", root.get("gloss", ""), source)
            root_nodes[root["id"]] = _graph_node(
                db,
                "root",
                root["label"],
                unit=unit,
                morpheme=morpheme,
                meta={"gloss": root.get("gloss", ""), "fam": root.get("fam", "")},
            )
            report.add("graph_nodes")

        branch_nodes: dict[str, GraphNode] = {}
        for branch in graph.get("branches", []):
            branch_nodes[branch["id"]] = _graph_node(
                db,
                "branch",
                branch["label"],
                unit=unit,
                meta={"root": branch.get("root", "")},
            )
            report.add("graph_nodes")

        for branch in graph.get("branches", []):
            parent = root_nodes.get(branch.get("root", ""))
            if parent:
                _edge(db, parent, branch_nodes[branch["id"]], "learning", "approved", source, "legacy words.js graph")
                report.add("edges")

        for link in graph.get("links", []):
            left = root_nodes.get(link.get("from")) or branch_nodes.get(link.get("from"))
            right = branch_nodes.get(link.get("to")) or word_nodes.get(link.get("to"))
            if not left or not right:
                continue
            relation = "semantic" if link.get("dash") else "learning"
            _edge(db, left, right, relation, "approved", source, link.get("rel", ""))
            report.add("edges")


def import_legacy_graph(db: Session, path: Path, report: Report) -> None:
    data = parse_legacy_graph(path)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    source = _source(db, "legacy:词族网络图.html", "legacy", str(path))
    book = _book(db, "Trellis 词族词库（fin/volv）", "从旧版深色词源图谱迁移的 20 词")
    unit = _unit(db, book, "fin / volv 词族", order_no=1, kind="family")

    fam_morphemes: dict[str, Morpheme] = {}
    node_map: dict[str, GraphNode] = {}
    roots = [node for node in nodes if node.get("type") == "root"]
    for node in roots:
        morpheme = _morpheme(db, node["label"], "root", node.get("gloss", ""), source)
        fam_morphemes[node.get("fam", node["label"])] = morpheme
        node_map[node["id"]] = _graph_node(
            db,
            "root",
            node["label"],
            unit=unit,
            morpheme=morpheme,
            meta={"fam": node.get("fam", ""), "gloss": node.get("gloss", "")},
        )
        report.add("graph_nodes")
        report.add("morphemes")

    branch_source = {}
    for node in nodes:
        if node.get("type") != "branch":
            continue
        branch_source[node["id"]] = node
        node_map[node["id"]] = _graph_node(
            db, "branch", node.get("label", node["id"]), unit=unit, meta={"fam": node.get("fam", "")}
        )
        report.add("graph_nodes")

    word_order = 0
    for node in nodes:
        if node.get("type") != "word":
            continue
        word_order += 1
        lexeme, created = get_or_create_lexeme(db, node["label"], "word", source.id)
        report.add("lexemes_created" if created else "lexemes_merged")
        ensure_spelling(db, lexeme, node["label"], "standard", True)
        ensure_pronunciation(db, lexeme, node.get("ipa", ""), "US", source.id)
        for index, text in enumerate(node.get("senses", []), start=1):
            if ensure_sense(db, lexeme, node.get("pos", ""), text, index, index == 1):
                report.add("senses")
        for collocation in node.get("coll", []):
            sense = db.scalar(
                select(Sense).where(Sense.lexeme_id == lexeme.id).order_by(Sense.order_no)
            )
            if sense:
                ensure_collocation(db, sense, _clean_html(collocation))
        example = db.scalar(
            select(Sense).where(Sense.lexeme_id == lexeme.id).order_by(Sense.order_no)
        )
        if example and node.get("ex"):
            ensure_example(db, example, _clean_html(node["ex"]))
        ensure_trait(db, lexeme, node.get("level", ""))
        _unit_word(db, unit, lexeme, word_order)
        _graph_node(db, "word", lexeme.headword, unit=unit, lexeme=lexeme)
        report.add("graph_nodes")
        node_map[node["id"]] = _graph_node(db, "word", lexeme.headword, unit=unit, lexeme=lexeme)
        fam = node.get("fam", "")
        if fam in fam_morphemes:
            _link_morpheme(db, lexeme, fam_morphemes[fam], "root", 0)
        formula = _clean_html(node.get("formula", ""))
        if formula:
            _pending_etymology(db, lexeme, formula, source, "旧版图谱构词公式")

    for edge in edges:
        left = node_map.get(edge.get("s"))
        right = node_map.get(edge.get("t"))
        if not left or not right:
            continue
        relation = "derivation" if edge.get("d") else "learning"
        status = "pending_review" if relation == "derivation" else "approved"
        _edge(db, left, right, relation, status, source, edge.get("p", ""))
        report.add("edges")
        if status == "pending_review":
            report.add("edges_pending")


def import_workbook(db: Session, path: Path, report: Report) -> None:
    sheets = parse_workbook(path)
    source = _source(db, "legacy:词族词库_fin-volv.xlsx", "legacy", str(path))
    book = _book(db, "Trellis 词族词库（fin/volv）", "从旧版深色词源图谱迁移的 20 词")
    unit = _unit(db, book, "fin / volv 词族", order_no=1, kind="family")

    word_nodes: dict[str, GraphNode] = {}
    for index, row in enumerate(sheets.get("词族总表", []), start=1):
        word = row.get("单词", "")
        if not word:
            continue
        raw_term = word
        term = _canonical_headword(raw_term)
        lexeme, created = get_or_create_lexeme(db, term, "word", source.id)
        report.add("lexemes_created" if created else "lexemes_merged")
        ensure_spelling(db, lexeme, term, "standard", True)
        if term != raw_term:
            _add_spelling_variants(db, lexeme, raw_term)
        ensure_pronunciation(db, lexeme, row.get("音标", ""), "US", source.id)
        definition = row.get("核心义（简）", "")
        if definition:
            if ensure_sense(db, lexeme, row.get("词性", ""), definition, 1, True):
                report.add("senses")
            ensure_trait(db, lexeme, row.get("主词层级", ""))
        fam = row.get("词族", "")
        root = row.get("词根义", "")
        prefix = row.get("前缀", "")
        if fam:
            root_m = _morpheme(db, fam, "root", root, source)
            _link_morpheme(db, lexeme, root_m, "root", 0)
            root_node = _graph_node(
                db, "root", fam, unit=unit, morpheme=root_m, meta={"gloss": root}
            )
            word_node = _graph_node(db, "word", lexeme.headword, unit=unit, lexeme=lexeme)
            word_nodes[word] = word_node
            _edge(db, root_node, word_node, "learning", "approved", source, "xlsx 词族总表")
        if prefix:
            prefix_form = re.sub(r"（.*?）|\(.*?\)", "", prefix).strip("-").strip()
            if prefix_form:
                prefix_m = _morpheme(db, prefix_form, "prefix", prefix, source)
                _link_morpheme(db, lexeme, prefix_m, "prefix", 1)
        formula = row.get("构词公式", "")
        if formula:
            _pending_etymology(db, lexeme, formula, source, "xlsx 构词公式")
        collocations = _split_semicolon(row.get("高频搭配 / 考点", ""))
        sense = db.scalar(
            select(Sense).where(Sense.lexeme_id == lexeme.id).order_by(Sense.order_no)
        )
        if sense:
            for item in collocations:
                ensure_collocation(db, sense, item)
        _unit_word(db, unit, lexeme, index)

    for row in sheets.get("主词判定", []):
        word = row.get("单词", "")
        if not word:
            continue
        lexeme = db.scalar(
            select(Lexeme).where(Lexeme.headword_norm == word.lower(), Lexeme.status == "active")
        )
        if lexeme:
            ensure_trait(
                db,
                lexeme,
                row.get("主词判定", ""),
                row.get("记忆成本", ""),
                row.get("处理建议", ""),
            )

    for row in sheets.get("构词结构", []):
        word = row.get("成品词", "")
        if not word:
            continue
        lexeme = db.scalar(
            select(Lexeme).where(Lexeme.headword_norm == word.lower(), Lexeme.status == "active")
        )
        if not lexeme:
            continue
        root_form = row.get("词根", "")
        root_gloss = row.get("词根义", "")
        prefix = row.get("前缀", "")
        if root_form:
            root_m = _morpheme(db, root_form, "root", root_gloss, source)
            _link_morpheme(db, lexeme, root_m, "root", 0)
        if prefix:
            prefix_m = _morpheme(db, prefix.strip("-"), "prefix", row.get("前缀义", ""), source)
            _link_morpheme(db, lexeme, prefix_m, "prefix", 1)
        logic = row.get("合成逻辑", "")
        if logic:
            root_node = _graph_node(db, "root", root_form, unit=unit)
            word_node = _graph_node(db, "word", lexeme.headword, unit=unit, lexeme=lexeme)
            _edge(db, root_node, word_node, "derivation", "pending_review", source, logic)
            report.add("edges_pending")

    for row in sheets.get("近义辨析", []):
        group_label = row.get("辨析组", "")
        word = row.get("词", "")
        if not group_label or not word:
            continue
        group = db.scalar(
            select(SenseContrastGroup).where(SenseContrastGroup.label == group_label)
        )
        if not group:
            group = SenseContrastGroup(label=group_label)
            db.add(group)
            db.flush()
        lexeme = db.scalar(
            select(Lexeme).where(Lexeme.headword_norm == word.lower(), Lexeme.status == "active")
        )
        if not lexeme:
            continue
        existing = db.scalar(
            select(SenseContrastItem).where(
                SenseContrastItem.group_id == group.id,
                SenseContrastItem.lexeme_id == lexeme.id,
            )
        )
        if existing:
            continue
        db.add(
            SenseContrastItem(
                group_id=group.id,
                lexeme_id=lexeme.id,
                distinction=row.get("核心区别", ""),
                collocations=row.get("典型搭配", ""),
                example_en=row.get("对比例句", ""),
            )
        )


def import_markdown(db: Session, path: Path, report: Report) -> None:
    entries = parse_markdown(path)
    source = _source(db, "legacy:词族知识库_fin-volv.md", "legacy", str(path))
    for entry in entries:
        raw_term = entry["word"]
        term = _canonical_headword(raw_term)
        lexeme, created = get_or_create_lexeme(db, term, "word", source.id)
        report.add("lexemes_created" if created else "lexemes_merged")
        ensure_spelling(db, lexeme, term, "standard", True)
        if term != raw_term:
            _add_spelling_variants(db, lexeme, raw_term)
        ensure_pronunciation(db, lexeme, entry.get("ipa", ""), "US", source.id)
        ensure_trait(db, lexeme, entry.get("level", ""))
        for index, text in enumerate(entry.get("senses", []), start=1):
            if ensure_sense(db, lexeme, entry.get("pos", ""), text, index, index == 1):
                report.add("senses")
        sense = db.scalar(
            select(Sense).where(Sense.lexeme_id == lexeme.id).order_by(Sense.order_no)
        )
        if sense:
            for collocation in entry.get("collocations", []):
                if collocation:
                    ensure_collocation(db, sense, _clean_html(collocation))
            for example in entry.get("examples", []):
                if example:
                    ensure_example(db, sense, _clean_html(example))
        if entry.get("construction"):
            _pending_etymology(db, lexeme, entry["construction"], source, "旧版知识库构词说明")
        if entry.get("notes"):
            trait = db.scalar(select(LexemeTrait).where(LexemeTrait.lexeme_id == lexeme.id))
            if trait and not trait.rationale:
                trait.rationale = entry["notes"]


def import_review_plan(db: Session, root: Path, report: Report) -> None:
    plan_path = root / "复习计划.md"
    if not plan_path.exists():
        report.notes.append("复习计划.md 不存在，跳过复习计划迁移")
        return
    source = _source(db, "legacy:复习计划.md", "legacy", str(plan_path))
    existing = db.scalar(select(StudyPlan).where(StudyPlan.name == "12 天词汇计划"))
    if existing:
        return
    plan = StudyPlan(
        name="12 天词汇计划",
        mode="fixed",
        start_date=date(2026, 11, 5),
        daily_target=20,
        status="active",
    )
    db.add(plan)
    db.flush()
    unit = db.scalar(select(Unit).where(Unit.title == "Day 1"))
    if unit:
        db.add(StudyPlanUnit(plan_id=plan.id, unit_id=unit.id, order_no=1, planned_date=date(2026, 11, 5)))
    report.add("study_plans")


def _normalize_spelling_variants(db: Session, report: Report) -> None:
    """Turn source forms such as ``labo(u)r`` into a standard headword plus variants.

    If a canonical lexeme already exists (for example after a first import run),
    the duplicate source-form entry is merged into it instead of being renamed.
    """
    for lexeme in db.scalars(select(Lexeme).where(Lexeme.headword.like("%(u)%"))).all():
        source_form = lexeme.headword
        standard = source_form.replace("(u)", "")
        british = source_form.replace("(u)", "u")
        if standard == source_form:
            continue
        target = db.scalar(
            select(Lexeme).where(
                Lexeme.headword_norm == standard.lower(),
                Lexeme.kind == lexeme.kind,
                Lexeme.id != lexeme.id,
            )
        )
        if target:
            for unit_word in db.scalars(
                select(UnitWord).where(UnitWord.lexeme_id == lexeme.id)
            ).all():
                duplicate = db.scalar(
                    select(UnitWord).where(
                        UnitWord.unit_id == unit_word.unit_id,
                        UnitWord.lexeme_id == target.id,
                    )
                )
                if duplicate:
                    db.delete(unit_word)
                else:
                    unit_word.lexeme_id = target.id
            for sense in db.scalars(select(Sense).where(Sense.lexeme_id == lexeme.id)).all():
                duplicate = db.scalar(
                    select(Sense).where(
                        Sense.lexeme_id == target.id,
                        Sense.pos == sense.pos,
                        Sense.definition_zh == sense.definition_zh,
                    )
                )
                if duplicate:
                    db.delete(sense)
                else:
                    sense.lexeme_id = target.id
            db.flush()
            for spelling in db.scalars(
                select(Spelling).where(Spelling.lexeme_id == lexeme.id)
            ).all():
                duplicate = db.scalar(
                    select(Spelling).where(
                        Spelling.lexeme_id == target.id,
                        Spelling.spelling == spelling.spelling,
                    )
                )
                if duplicate:
                    db.delete(spelling)
                else:
                    spelling.lexeme_id = target.id
            db.flush()
            db.delete(lexeme)
            db.flush()
            lexeme = target
            report.add("duplicate_source_forms_merged")
        else:
            lexeme.headword = standard
            lexeme.headword_norm = standard.lower()
        for spelling, variant in (
            (standard, "standard"),
            (british, "british"),
            (source_form, "source_form"),
        ):
            existing_spelling = db.scalar(
                select(Spelling).where(
                    Spelling.lexeme_id == lexeme.id, Spelling.spelling == spelling
                )
            )
            if existing_spelling:
                existing_spelling.variant_type = variant
                existing_spelling.is_primary = spelling == standard
            else:
                ensure_spelling(db, lexeme, spelling, variant, spelling == standard)
        report.add("spelling_variants")
    for spelling in db.scalars(select(Spelling).where(Spelling.spelling.like("%(u)%"))).all():
        spelling.variant_type = "source_form"
        spelling.is_primary = False
    db.flush()


def run_legacy_import(db: Session, root: Path) -> dict:
    report = Report()
    words_js = root / "data" / "words.js"
    legacy_html = root / "词族网络图.html"
    workbook = root / "词族词库_fin-volv.xlsx"
    markdown = root / "词族知识库_fin-volv.md"

    if words_js.exists():
        import_words_js(db, words_js, report)
    else:
        report.notes.append("data/words.js 不存在，跳过")
    if legacy_html.exists():
        import_legacy_graph(db, legacy_html, report)
    else:
        report.notes.append("词族网络图.html 不存在，跳过")
    if workbook.exists():
        import_workbook(db, workbook, report)
    else:
        report.notes.append("词族词库_fin-volv.xlsx 不存在，跳过")
    if markdown.exists():
        import_markdown(db, markdown, report)
    else:
        report.notes.append("词族知识库_fin-volv.md 不存在，跳过")
    import_review_plan(db, root, report)
    _normalize_spelling_variants(db, report)

    from app.services.reviews import ensure_cards_for_lexeme

    for lexeme in db.scalars(select(Lexeme).where(Lexeme.status == "active")).all():
        ensure_cards_for_lexeme(db, lexeme, mode="fsrs")
        report.add("cards")

    db.commit()
    return report.as_dict()
