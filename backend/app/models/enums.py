"""Shared enums and validation constants for the Trellis schema."""

from __future__ import annotations

LEXEME_KINDS = ("word", "phrase", "morpheme")
LEXEME_STATUS = ("active", "archived")

SPELLING_VARIANTS = ("standard", "british", "american", "source_form")

MORPHEME_TYPES = ("root", "prefix", "suffix", "combining")

RELATION_TYPES = ("etymology", "derivation", "phrase", "semantic", "thematic", "learning")

EDGE_STATUS = ("pending_review", "approved", "rejected")

CONFIDENCE = ("low", "medium", "high")

CARD_TYPES = ("en_to_zh", "zh_to_en", "spelling", "derivation", "collocation")

REVIEW_MODES = ("fixed", "fsrs")

REVIEW_RESULTS = ("again", "hard", "good", "easy")

STUDY_EVENT_TYPES = ("learn", "review", "import", "edit")

IMPORT_STATUS = ("pending", "parsed", "previewed", "committed", "failed", "rolled_back")

IMPORT_ACTIONS = ("created", "merged", "skipped", "error")

BOOK_UNIT_KINDS = ("family", "day", "unit", "custom")
