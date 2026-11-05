from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GraphEdge, GraphLayout, GraphNode


def _node_dict(node: GraphNode) -> dict:
    try:
        meta = json.loads(node.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    return {
        "id": node.id,
        "node_type": node.node_type,
        "label": node.label,
        "lexeme_id": node.lexeme_id,
        "morpheme_id": node.morpheme_id,
        "unit_id": node.unit_id,
        "meta": meta,
    }


def _edge_dict(edge: GraphEdge) -> dict:
    return {
        "id": edge.id,
        "source_node_id": edge.source_node_id,
        "target_node_id": edge.target_node_id,
        "relation_type": edge.relation_type,
        "status": edge.status,
        "directed": edge.directed,
        "evidence": edge.evidence,
    }


def get_view(
    db: Session,
    *,
    unit_id: int | None = None,
    node_id: int | None = None,
    depth: int = 2,
    relation_type: str | None = None,
    status: str | None = None,
    limit: int = 600,
) -> dict:
    seed: GraphNode | None = None
    if node_id:
        seed = db.get(GraphNode, node_id)
    collected: dict[int, GraphNode] = {}
    if seed:
        frontier = {seed.id}
        collected[seed.id] = seed
        for _ in range(max(1, min(depth, 4))):
            if not frontier:
                break
            next_frontier: set[int] = set()
            rows = db.scalars(
                select(GraphEdge).where(
                    (GraphEdge.source_node_id.in_(frontier))
                    | (GraphEdge.target_node_id.in_(frontier))
                )
            ).all()
            for edge in rows:
                for other_id in (edge.source_node_id, edge.target_node_id):
                    if other_id in collected:
                        continue
                    other = db.get(GraphNode, other_id)
                    if other:
                        collected[other_id] = other
                        next_frontier.add(other_id)
            frontier = next_frontier
    else:
        stmt = select(GraphNode)
        if unit_id:
            stmt = stmt.where(GraphNode.unit_id == unit_id)
        nodes = db.scalars(stmt.order_by(GraphNode.id).limit(limit + 1)).all()
        if len(nodes) > limit:
            nodes = nodes[:limit]
        for node in nodes:
            collected[node.id] = node

    ids = set(collected)
    edge_stmt = select(GraphEdge).where(
        GraphEdge.source_node_id.in_(ids), GraphEdge.target_node_id.in_(ids)
    )
    if relation_type:
        edge_stmt = edge_stmt.where(GraphEdge.relation_type == relation_type)
    if status:
        edge_stmt = edge_stmt.where(GraphEdge.status == status)
    edges = db.scalars(edge_stmt.order_by(GraphEdge.id).limit(limit * 3)).all()

    return {
        "nodes": [_node_dict(node) for node in collected.values()],
        "edges": [_edge_dict(edge) for edge in edges],
        "truncated": not seed and len(collected) >= limit,
    }


def neighbors(db: Session, node_id: int, depth: int = 1) -> dict:
    return get_view(db, node_id=node_id, depth=depth)


def create_edge(db: Session, payload) -> GraphEdge:
    edge = GraphEdge(
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        relation_type=payload.relation_type,
        status=payload.status,
        directed=payload.directed,
        evidence=payload.evidence,
        weight=payload.weight,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def update_edge(db: Session, edge: GraphEdge, payload) -> GraphEdge:
    if payload.relation_type:
        edge.relation_type = payload.relation_type
    if payload.status:
        edge.status = payload.status
    if payload.evidence is not None:
        edge.evidence = payload.evidence
    if payload.weight is not None:
        edge.weight = payload.weight
    db.commit()
    db.refresh(edge)
    return edge


def delete_edge(db: Session, edge: GraphEdge) -> None:
    db.delete(edge)
    db.commit()


def list_layouts(db: Session) -> list[GraphLayout]:
    return list(db.scalars(select(GraphLayout).order_by(GraphLayout.id)).all())


def upsert_layout(db: Session, payload) -> GraphLayout:
    layout = db.scalar(select(GraphLayout).where(GraphLayout.name == payload.name))
    if layout:
        layout.view = payload.view
        layout.data_json = json.dumps(payload.data, ensure_ascii=False)
    else:
        layout = GraphLayout(
            name=payload.name,
            view=payload.view,
            data_json=json.dumps(payload.data, ensure_ascii=False),
        )
        db.add(layout)
    db.commit()
    db.refresh(layout)
    return layout
