from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (UniqueConstraint("name", name="uq_data_sources_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="file")
    path: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        CheckConstraint("node_type IN ('root','branch','word','affix')", name="node_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    node_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    lexeme_id: Mapped[int | None] = mapped_column(
        ForeignKey("lexemes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    morpheme_id: Mapped[int | None] = mapped_column(
        ForeignKey("morphemes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('etymology','derivation','phrase','semantic','thematic','learning')",
            name="edge_relation_type",
        ),
        CheckConstraint(
            "status IN ('pending_review','approved','rejected')", name="edge_status"
        ),
        UniqueConstraint(
            "source_node_id", "target_node_id", "relation_type", name="uq_edge_triplet"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_node_id: Mapped[int] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[int] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(24), nullable=False, default="learning")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="approved")
    directed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class GraphLayout(Base):
    __tablename__ = "graph_layouts"
    __table_args__ = (UniqueConstraint("name", name="uq_graph_layouts_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    view: Mapped[str] = mapped_column(String(32), nullable=False, default="explore")
    data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GraphReviewQueue(Base):
    __tablename__ = "graph_review_queue"
    __table_args__ = (
        UniqueConstraint("edge_id", name="uq_review_edge"),
        CheckConstraint(
            "status IN ('pending_review','approved','rejected')", name="review_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    edge_id: Mapped[int] = mapped_column(
        ForeignKey("graph_edges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_review")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
