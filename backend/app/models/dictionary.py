from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lexeme(Base):
    """A canonical dictionary entry: word, phrase or bound morpheme."""

    __tablename__ = "lexemes"
    __table_args__ = (
        UniqueConstraint("headword_norm", "kind", "homograph_no", name="uq_lexemes_key"),
        CheckConstraint("kind IN ('word','phrase','morpheme')", name="lexeme_kind"),
        CheckConstraint("status IN ('active','archived')", name="lexeme_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    headword: Mapped[str] = mapped_column(String(120), nullable=False)
    headword_norm: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="word")
    homograph_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    spellings: Mapped[list["Spelling"]] = relationship(
        back_populates="lexeme",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Spelling.id",
    )
    pronunciations: Mapped[list["Pronunciation"]] = relationship(
        back_populates="lexeme",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Pronunciation.id",
    )
    senses: Mapped[list["Sense"]] = relationship(
        back_populates="lexeme",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Sense.order_no",
    )
    etymologies: Mapped[list["Etymology"]] = relationship(
        back_populates="lexeme",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Etymology.id",
    )
    trait: Mapped["LexemeTrait | None"] = relationship(
        back_populates="lexeme",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


class Spelling(Base):
    __tablename__ = "spellings"
    __table_args__ = (
        UniqueConstraint("lexeme_id", "spelling", name="uq_spellings_lexeme_spelling"),
        CheckConstraint(
            "variant_type IN ('standard','british','american','source_form')",
            name="spelling_variant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    spelling: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    variant_type: Mapped[str] = mapped_column(String(16), nullable=False, default="standard")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    lexeme: Mapped["Lexeme"] = relationship(back_populates="spellings")


class Pronunciation(Base):
    __tablename__ = "pronunciations"
    __table_args__ = (UniqueConstraint("lexeme_id", "ipa", "accent", name="uq_pronunciation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ipa: Mapped[str] = mapped_column(String(120), nullable=False)
    accent: Mapped[str] = mapped_column(String(16), nullable=False, default="US")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )

    lexeme: Mapped["Lexeme"] = relationship(back_populates="pronunciations")


class Sense(Base):
    __tablename__ = "senses"
    __table_args__ = (
        UniqueConstraint("lexeme_id", "order_no", name="uq_senses_order"),
        CheckConstraint("order_no >= 1", name="sense_order_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pos: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    definition_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    definition_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    lexeme: Mapped["Lexeme"] = relationship(back_populates="senses")
    examples: Mapped[list["Example"]] = relationship(
        back_populates="sense",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Example.order_no",
    )
    collocations: Mapped[list["Collocation"]] = relationship(
        back_populates="sense",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Collocation.id",
    )


class Example(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("senses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    translation_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )

    sense: Mapped["Sense"] = relationship(back_populates="examples")


class Collocation(Base):
    __tablename__ = "collocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("senses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pattern: Mapped[str] = mapped_column(String(240), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    sense: Mapped["Sense"] = relationship(back_populates="collocations")


class Morpheme(Base):
    __tablename__ = "morphemes"
    __table_args__ = (
        UniqueConstraint("form", "type", name="uq_morphemes_form_type"),
        CheckConstraint("type IN ('root','prefix','suffix','combining')", name="morpheme_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    form: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="root")
    gloss_zh: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )


class LexemeMorpheme(Base):
    __tablename__ = "lexeme_morphemes"
    __table_args__ = (
        UniqueConstraint("lexeme_id", "morpheme_id", "role", name="uq_lexeme_morpheme"),
        CheckConstraint("role IN ('root','prefix','suffix','combining')", name="lm_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    morpheme_id: Mapped[int] = mapped_column(
        ForeignKey("morphemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="root")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Etymology(Base):
    __tablename__ = "etymologies"
    __table_args__ = (
        CheckConstraint("confidence IN ('low','medium','high')", name="etymology_confidence"),
        CheckConstraint(
            "status IN ('pending_review','approved','rejected')", name="etymology_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending_review")
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )

    lexeme: Mapped["Lexeme"] = relationship(back_populates="etymologies")


class LexemeTrait(Base):
    __tablename__ = "lexeme_traits"

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    main_level: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    memory_cost: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    advice: Mapped[str] = mapped_column(Text, nullable=False, default="")

    lexeme: Mapped["Lexeme"] = relationship(back_populates="trait")


class SenseContrastGroup(Base):
    __tablename__ = "sense_contrast_groups"
    __table_args__ = (UniqueConstraint("label", name="uq_contrast_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")


class SenseContrastItem(Base):
    __tablename__ = "sense_contrast_items"
    __table_args__ = (UniqueConstraint("group_id", "lexeme_id", name="uq_contrast_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("sense_contrast_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lexeme_id: Mapped[int] = mapped_column(
        ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sense_id: Mapped[int | None] = mapped_column(
        ForeignKey("senses.id", ondelete="SET NULL"), nullable=True
    )
    distinction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    collocations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    example_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    example_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
