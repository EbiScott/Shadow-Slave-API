from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import HTTPException

from app.config import database_path
from app.extraction import canonical_character


def connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise HTTPException(status_code=503, detail="Quote database is not built")
    uri = path.as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Quote database is unavailable") from error
    connection.row_factory = sqlite3.Row
    return connection


def get_db():
    connection = connect(database_path())
    try:
        yield connection
    finally:
        connection.close()


def resolve_character(connection: sqlite3.Connection, name: str) -> str | None:
    keys = [name.strip().lower()]
    canonical = canonical_character(name)
    if canonical:
        keys.append(canonical.lower())
    for key in keys:
        if not key:
            continue
        row = connection.execute(
            "SELECT character FROM aliases WHERE alias = ?",
            (key,),
        ).fetchone()
        if row:
            return row["character"]
    row = connection.execute(
        "SELECT DISTINCT character FROM quotes WHERE lower(character) = ? LIMIT 1",
        (keys[0],),
    ).fetchone()
    return row["character"] if row else None


def meta(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT key, value FROM meta").fetchall()
    return {row["key"]: row["value"] for row in rows}
