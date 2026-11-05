from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.graph import EdgeCreate, EdgeUpdate, GraphView, LayoutRead, LayoutUpsert
from app.services import graph as service

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
def get_graph(
    unit_id: int | None = None,
    node_id: int | None = None,
    depth: int = Query(2, ge=1, le=4),
    relation_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return service.get_view(
        db,
        unit_id=unit_id,
        node_id=node_id,
        depth=depth,
        relation_type=relation_type,
        status=status,
    )


@router.get("/nodes/{node_id}")
def get_node(node_id: int, db: Session = Depends(get_db)):
    from app.models import GraphNode

    node = db.get(GraphNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="node not found")
    return service._node_dict(node)


@router.get("/nodes/{node_id}/neighbors")
def get_neighbors(node_id: int, depth: int = Query(1, ge=1, le=3), db: Session = Depends(get_db)):
    return service.neighbors(db, node_id, depth=depth)


@router.post("/edges", status_code=201)
def create_edge(payload: EdgeCreate, db: Session = Depends(get_db)):
    try:
        edge = service.create_edge(db, payload)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return service._edge_dict(edge)


@router.patch("/edges/{edge_id}")
def update_edge(edge_id: int, payload: EdgeUpdate, db: Session = Depends(get_db)):
    from app.models import GraphEdge

    edge = db.get(GraphEdge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="edge not found")
    return service._edge_dict(service.update_edge(db, edge, payload))


@router.delete("/edges/{edge_id}")
def delete_edge(edge_id: int, db: Session = Depends(get_db)):
    from app.models import GraphEdge

    edge = db.get(GraphEdge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="edge not found")
    service.delete_edge(db, edge)
    return {"ok": True}


@router.get("/layouts", response_model=list[LayoutRead])
def list_layouts(db: Session = Depends(get_db)):
    return [
        {
            "id": layout.id,
            "name": layout.name,
            "view": layout.view,
            "data": json.loads(layout.data_json or "{}"),
        }
        for layout in service.list_layouts(db)
    ]


@router.put("/layouts")
def upsert_layout(payload: LayoutUpsert, db: Session = Depends(get_db)):
    layout = service.upsert_layout(db, payload)
    return {"id": layout.id, "name": layout.name, "view": layout.view}
