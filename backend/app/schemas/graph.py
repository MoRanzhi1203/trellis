from __future__ import annotations

from pydantic import BaseModel, Field


class GraphNodeRead(BaseModel):
    id: int
    node_type: str
    label: str
    lexeme_id: int | None = None
    morpheme_id: int | None = None
    unit_id: int | None = None
    meta: dict = Field(default_factory=dict)


class GraphEdgeRead(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    relation_type: str
    status: str
    directed: bool
    evidence: str = ""


class GraphView(BaseModel):
    nodes: list[GraphNodeRead]
    edges: list[GraphEdgeRead]
    truncated: bool = False


class GraphNodeCreate(BaseModel):
    node_type: str
    label: str
    lexeme_id: int | None = None
    morpheme_id: int | None = None
    unit_id: int | None = None
    meta: dict = Field(default_factory=dict)


class EdgeCreate(BaseModel):
    source_node_id: int
    target_node_id: int
    relation_type: str = "learning"
    status: str = "approved"
    directed: bool = True
    evidence: str = ""
    weight: float = 1.0


class EdgeUpdate(BaseModel):
    relation_type: str | None = None
    status: str | None = None
    evidence: str | None = None
    weight: float | None = None


class LayoutRead(BaseModel):
    id: int
    name: str
    view: str
    data: dict


class LayoutUpsert(BaseModel):
    name: str
    view: str = "explore"
    data: dict = Field(default_factory=dict)
