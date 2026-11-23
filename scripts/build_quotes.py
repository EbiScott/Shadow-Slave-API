from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.extraction import (  # noqa: E402
    AUTHOR,
    BOOK,
    canonical_character,
    extract_quotes_from_epub,
    iter_epubs,
)

SCHEMA = """
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character TEXT NOT NULL,
    character_raw TEXT NOT NULL,
    quote TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    volume INTEGER NOT NULL,
    volume_title TEXT NOT NULL,
    chapter TEXT NOT NULL,
    chapter_index INTEGER NOT NULL,
    quote_index INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    confidence TEXT NOT NULL,
    UNIQUE(character, quote)
);

CREATE INDEX idx_quotes_character ON quotes(character);
CREATE INDEX idx_quotes_volume ON quotes(volume);
CREATE INDEX idx_quotes_length ON quotes(word_count, char_count);

CREATE TABLE aliases (
    alias TEXT PRIMARY KEY,
    character TEXT NOT NULL
);

CREATE INDEX idx_aliases_character ON aliases(character);
"""


def build(source_dir: Path, output: Path) -> None:
    epubs = list(iter_epubs(source_dir))
    if not epubs:
        raise SystemExit(f"No EPUB files found in {source_dir}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".db.tmp")
    if temporary.exists():
        temporary.unlink()

    connection = sqlite3.connect(temporary)
    try:
        connection.executescript(SCHEMA)
        aliases: dict[str, str] = {}
        seen: set[tuple[str, str]] = set()
        count = 0
        volume_counts: list[tuple[Path, int]] = []

        for epub in epubs:
            quotes = extract_quotes_from_epub(epub)
            added = 0
            for quote in quotes:
                key = (quote.character, quote.quote)
                if key in seen:
                    continue
                seen.add(key)
                added += 1
                connection.execute(
                    """
                    INSERT INTO quotes (
                        character, character_raw, quote, word_count, char_count,
                        volume, volume_title, chapter, chapter_index, quote_index,
                        source_file, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        quote.character,
                        quote.character_raw,
                        quote.quote,
                        quote.word_count,
                        quote.char_count,
                        quote.volume,
                        quote.volume_title,
                        quote.chapter,
                        quote.chapter_index,
                        quote.quote_index,
                        quote.source_file,
                        quote.confidence,
                    ),
                )
                count += 1
                aliases[quote.character.lower()] = quote.character
                aliases[quote.character_raw.strip().lower()] = quote.character
                canonical = canonical_character(quote.character_raw)
                if canonical:
                    aliases[canonical.lower()] = canonical
            volume_counts.append((epub, added))

        for alias, character in aliases.items():
            if not alias:
                continue
            connection.execute(
                "INSERT OR IGNORE INTO aliases (alias, character) VALUES (?, ?)",
                (alias, character),
            )

        character_count = connection.execute(
            "SELECT COUNT(DISTINCT character) FROM quotes"
        ).fetchone()[0]
        meta = {
            "book": BOOK,
            "author": AUTHOR,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "quote_count": str(count),
            "character_count": str(character_count),
            "volume_count": str(len(epubs)),
            "source_files": ", ".join(path.name for path in epubs),
            "schema_version": "1",
        }
        connection.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            meta.items(),
        )
        connection.commit()
    finally:
        connection.close()

    if output.exists():
        output.unlink()
    temporary.replace(output)

    print(f"Wrote {count} quotes and {character_count} characters to {output}")
    for epub, volume_quotes in volume_counts:
        print(f"  {epub.name}: {volume_quotes} attributed lines")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "quotes.db")
    args = parser.parse_args()
    build(args.source_dir, args.output)


if __name__ == "__main__":
    main()
