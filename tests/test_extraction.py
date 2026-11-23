from __future__ import annotations

import zipfile

from app.extraction import (
    canonical_character,
    extract_quotes_from_epub,
    quote_spans,
)


def _epub(tmp_path, filename: str, body: str):
    path = tmp_path / filename
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("EPUB/content/chapter.xhtml", f"<html><body>{body}</body></html>")
    return path


def test_quote_spans_reads_straight_and_curly_quotes():
    assert [span.text for span in quote_spans('“First line.”')] == ["First line."]
    assert [span.text for span in quote_spans('"Second line."')] == ["Second line."]


def test_canonical_character_resolves_aliases_and_rejects_noise():
    assert canonical_character("Sunny") == "Sunless"
    assert canonical_character("Neph") == "Nephis"
    assert canonical_character("Cassia") == "Cassie"
    assert canonical_character("After") is None
    assert canonical_character("As Sunny") is None


def test_h3_chapter_headings_extract_quotes(tmp_path):
    path = _epub(
        tmp_path,
        "Shadow Slave - Vol. 6 - Test.epub",
        (
            "<h3>Chapter 1201 Test</h3>"
            "<p>“We keep moving,” Sunny said.</p>"
            "<p>“Fine, we can leave in the morning,” Nephis said.</p>"
        ),
    )

    quotes = extract_quotes_from_epub(path)

    assert [quote.character for quote in quotes] == ["Sunless", "Nephis"]
    assert {quote.chapter for quote in quotes} == {"Chapter 1201 Test"}


def test_multiple_h1_chapters_stay_separate(tmp_path):
    path = _epub(
        tmp_path,
        "Shadow Slave - Vol. 10 - Test.epub",
        (
            "<h1>Chapter 1</h1><p>“One, we should leave at dawn,” Sunny said.</p>"
            "<h1>Chapter 2</h1><p>“Two, we should leave at dusk,” Nephis said.</p>"
        ),
    )

    quotes = extract_quotes_from_epub(path)

    assert [quote.chapter for quote in quotes] == ["Chapter 1", "Chapter 2"]
