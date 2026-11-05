from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    total: int
    offset: int
    limit: int
    items: list


class ExampleIn(BaseModel):
    text: str
    translation_zh: str = ""
    order_no: int = 1


class ExampleRead(ORMModel):
    id: int
    text: str
    translation_zh: str
    order_no: int


class CollocationIn(BaseModel):
    pattern: str
    note: str = ""


class CollocationRead(ORMModel):
    id: int
    pattern: str
    note: str


class SenseIn(BaseModel):
    pos: str = ""
    definition_zh: str = ""
    definition_en: str = ""
    order_no: int = 1
    examples: list[ExampleIn] = Field(default_factory=list)
    collocations: list[CollocationIn] = Field(default_factory=list)


class SenseRead(ORMModel):
    id: int
    pos: str
    definition_zh: str
    definition_en: str
    order_no: int
    is_primary: bool
    examples: list[ExampleRead] = Field(default_factory=list)
    collocations: list[CollocationRead] = Field(default_factory=list)


class SpellingIn(BaseModel):
    spelling: str
    variant_type: str = "standard"
    is_primary: bool = False


class SpellingRead(ORMModel):
    id: int
    spelling: str
    variant_type: str
    is_primary: bool


class PronunciationIn(BaseModel):
    ipa: str
    accent: str = "US"


class PronunciationRead(ORMModel):
    id: int
    ipa: str
    accent: str


class EtymologyRead(ORMModel):
    id: int
    description_zh: str
    confidence: str
    status: str
    evidence: str


class TraitRead(ORMModel):
    id: int
    main_level: str
    memory_cost: str
    rationale: str
    advice: str


class LexemeRead(ORMModel):
    id: int
    headword: str
    kind: str
    status: str
    created_at: datetime
    updated_at: datetime
    spellings: list[SpellingRead] = Field(default_factory=list)
    pronunciations: list[PronunciationRead] = Field(default_factory=list)
    senses: list[SenseRead] = Field(default_factory=list)
    etymologies: list[EtymologyRead] = Field(default_factory=list)
    trait: TraitRead | None = None


class LexemeCreate(BaseModel):
    headword: str = Field(min_length=1, max_length=120)
    kind: str = "word"
    homograph_no: int = 1
    spellings: list[SpellingIn] = Field(default_factory=list)
    pronunciations: list[PronunciationIn] = Field(default_factory=list)
    senses: list[SenseIn] = Field(default_factory=list)
    main_level: str | None = None
    memory_cost: str | None = None


class LexemeUpdate(BaseModel):
    headword: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = None
    status: str | None = None
    spellings: list[SpellingIn] | None = None
    pronunciations: list[PronunciationIn] | None = None
    senses: list[SenseIn] | None = None
    main_level: str | None = None
    memory_cost: str | None = None


class SearchHit(BaseModel):
    id: int
    headword: str
    kind: str
    snippet: str
