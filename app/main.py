from __future__ import annotations

import sqlite3
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import allowed_origins
from app.db import get_db, meta, resolve_character
from app.extraction import AUTHOR, BOOK
from app.models import (
    CharacterDetail,
    CharacterList,
    CharacterSummary,
    Health,
    Quote,
    QuoteList,
)

app = FastAPI(
    title="Shadow Slave Quote API",
    version="1.0.0",
    description=(
        "Short, explicitly attributed dialogue from Shadow Slave. "
        "The API serves quotes, not book text."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

ATTRIBUTION = f"{BOOK} by {AUTHOR}"


def _quote(row: sqlite3.Row) -> Quote:
    return Quote(
        id=row["id"],
        character=row["character"],
        quote=row["quote"],
        book=BOOK,
        author=AUTHOR,
        volume=row["volume"],
        volume_title=row["volume_title"],
        chapter=row["chapter"],
        attribution=ATTRIBUTION,
    )


def _quote_by_id(connection: sqlite3.Connection, quote_id: int) -> Optional[Quote]:
    row = connection.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    return _quote(row) if row else None


def _character_summary(row: sqlite3.Row) -> CharacterSummary:
    aliases = [value for value in (row["aliases"] or "").split(",") if value]
    volumes = sorted({int(value) for value in (row["volume_list"] or "").split(",") if value})
    return CharacterSummary(
        character=row["character"],
        quote_count=row["quote_count"],
        aliases=aliases,
        volumes=volumes,
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "Shadow Slave Quote API",
        "docs": "/docs",
        "health": "/health",
        "random_sunless": "/v1/quotes/random?character=Sunless",
    }


@app.get("/health", response_model=Health)
def health(connection: sqlite3.Connection = Depends(get_db)) -> Health:
    values = meta(connection)
    return Health(
        status="ok",
        book=values.get("book", BOOK),
        author=values.get("author", AUTHOR),
        quote_count=int(values.get("quote_count", "0")),
        character_count=int(values.get("character_count", "0")),
        volume_count=int(values.get("volume_count", "0")),
        generated_at=values.get("generated_at", ""),
    )


@app.get("/v1/characters", response_model=CharacterList)
def characters(
    q: Optional[str] = Query(None, min_length=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    connection: sqlite3.Connection = Depends(get_db),
) -> CharacterList:
    term = f"%{q.strip()}%" if q else None
    base = connection.execute(
        """
        SELECT
            q.character AS character,
            COUNT(DISTINCT q.id) AS quote_count,
            GROUP_CONCAT(DISTINCT a.alias) AS aliases,
            GROUP_CONCAT(DISTINCT q.volume) AS volume_list
        FROM quotes q
        LEFT JOIN aliases a ON a.character = q.character
        GROUP BY q.character
        HAVING (? IS NULL OR lower(q.character) LIKE lower(?) OR lower(GROUP_CONCAT(DISTINCT a.alias)) LIKE lower(?))
        ORDER BY quote_count DESC, q.character COLLATE NOCASE ASC
        """,
        (term, term, term),
    ).fetchall()
    total = len(base)
    items = [_character_summary(row) for row in base[offset : offset + limit]]
    return CharacterList(total=total, limit=limit, offset=offset, items=items)


@app.get("/v1/characters/{character}", response_model=CharacterDetail)
def character(
    character: str,
    connection: sqlite3.Connection = Depends(get_db),
) -> CharacterDetail:
    canonical = resolve_character(connection, character)
    if not canonical:
        raise HTTPException(status_code=404, detail="Character not found")

    summary_row = connection.execute(
        """
        SELECT
            q.character AS character,
            COUNT(DISTINCT q.id) AS quote_count,
            GROUP_CONCAT(DISTINCT a.alias) AS aliases,
            GROUP_CONCAT(DISTINCT q.volume) AS volume_list
        FROM quotes q
        LEFT JOIN aliases a ON a.character = q.character
        WHERE q.character = ?
        GROUP BY q.character
        """,
        (canonical,),
    ).fetchone()
    if not summary_row:
        raise HTTPException(status_code=404, detail="Character not found")

    first_row = connection.execute(
        "SELECT * FROM quotes WHERE character = ? ORDER BY volume, id LIMIT 1",
        (canonical,),
    ).fetchone()
    last_row = connection.execute(
        "SELECT * FROM quotes WHERE character = ? ORDER BY volume DESC, id DESC LIMIT 1",
        (canonical,),
    ).fetchone()
    summary = _character_summary(summary_row)
    return CharacterDetail(
        character=summary.character,
        quote_count=summary.quote_count,
        aliases=summary.aliases,
        volumes=summary.volumes,
        first_quote=_quote(first_row) if first_row else None,
        last_quote=_quote(last_row) if last_row else None,
    )


@app.get("/v1/quotes/random", response_model=Quote)
def random_quote(
    response: Response,
    character: Optional[str] = Query(None, min_length=1),
    volume: Optional[int] = Query(None, ge=1, le=99),
    min_words: int = Query(3, ge=1, le=100),
    max_chars: int = Query(280, ge=20, le=2000),
    connection: sqlite3.Connection = Depends(get_db),
) -> Quote:
    where = ["word_count >= ?", "char_count <= ?"]
    params: list[object] = [min_words, max_chars]

    if character:
        canonical = resolve_character(connection, character)
        if not canonical:
            raise HTTPException(status_code=404, detail="Character not found")
        where.append("character = ?")
        params.append(canonical)
    if volume:
        where.append("volume = ?")
        params.append(volume)

    row = connection.execute(
        f"SELECT * FROM quotes WHERE {' AND '.join(where)} ORDER BY RANDOM() LIMIT 1",
        params,
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="No quotes matched those filters; try a lower min_words or higher max_chars",
        )
    response.headers["Cache-Control"] = "no-store"
    return _quote(row)


@app.get("/v1/quotes", response_model=QuoteList)
def quotes(
    q: Optional[str] = Query(None, min_length=1),
    character: Optional[str] = Query(None, min_length=1),
    volume: Optional[int] = Query(None, ge=1, le=99),
    confidence: Optional[str] = Query(None, pattern="^(tag|action)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    connection: sqlite3.Connection = Depends(get_db),
) -> QuoteList:
    where: list[str] = []
    params: list[object] = []

    if q:
        where.append("quote LIKE ?")
        params.append(f"%{q.strip()}%")
    if character:
        canonical = resolve_character(connection, character)
        if not canonical:
            raise HTTPException(status_code=404, detail="Character not found")
        where.append("character = ?")
        params.append(canonical)
    if volume:
        where.append("volume = ?")
        params.append(volume)
    if confidence:
        where.append("confidence = ?")
        params.append(confidence)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = connection.execute(
        f"SELECT COUNT(*) FROM quotes {clause}",
        params,
    ).fetchone()[0]
    rows = connection.execute(
        f"SELECT * FROM quotes {clause} ORDER BY id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return QuoteList(
        total=total,
        limit=limit,
        offset=offset,
        items=[_quote(row) for row in rows],
    )


@app.get("/v1/quotes/{quote_id}", response_model=Quote)
def quote(quote_id: int, connection: sqlite3.Connection = Depends(get_db)) -> Quote:
    result = _quote_by_id(connection, quote_id)
    if not result:
        raise HTTPException(status_code=404, detail="Quote not found")
    return result
