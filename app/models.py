from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Quote(BaseModel):
    id: int
    character: str
    quote: str
    book: str
    author: str
    volume: int
    volume_title: str
    chapter: str
    attribution: str


class QuoteList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Quote]


class CharacterSummary(BaseModel):
    character: str
    quote_count: int
    aliases: List[str]
    volumes: List[int]


class CharacterList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[CharacterSummary]


class CharacterDetail(BaseModel):
    character: str
    quote_count: int
    aliases: List[str]
    volumes: List[int]
    first_quote: Optional[Quote]
    last_quote: Optional[Quote]


class Health(BaseModel):
    status: str
    book: str
    author: str
    quote_count: int
    character_count: int
    volume_count: int
    generated_at: str
