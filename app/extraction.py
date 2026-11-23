from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

BOOK = "Shadow Slave"
AUTHOR = "Guiltythree"

SPEECH_VERBS = (
    "said",
    "asked",
    "replied",
    "answered",
    "added",
    "muttered",
    "whispered",
    "shouted",
    "yelled",
    "called",
    "continued",
    "explained",
    "sighed",
    "laughed",
    "snapped",
    "agreed",
    "admitted",
    "murmured",
    "growled",
    "hissed",
    "noted",
    "observed",
    "remarked",
    "responded",
    "retorted",
    "warned",
    "began",
    "finished",
    "mumbled",
    "announced",
    "declared",
    "stated",
    "insisted",
    "promised",
    "wondered",
    "repeated",
    "corrected",
    "interrupted",
    "concluded",
    "offered",
    "suggested",
    "urged",
    "pleaded",
    "roared",
    "screamed",
    "breathed",
    "spat",
)
BODY_VERBS = (
    "grinned",
    "smiled",
    "nodded",
    "shrugged",
    "frowned",
    "chuckled",
    "scoffed",
    "snorted",
    "huffed",
    "teased",
    "joked",
    "sneered",
)
VERBS = SPEECH_VERBS + BODY_VERBS
VERB_PATTERN = "|".join(VERBS)
SPEECH_VERB_PATTERN = "|".join(SPEECH_VERBS)
NAME_PATTERN = r"[A-Z][A-Za-z’'\-]+(?:\s+(?:(?:of|the|de|van|von)\s+)?[A-Z][A-Za-z’'\-]+){0,3}"
NAME_RE = re.compile(NAME_PATTERN)
TAG_AFTER_INVERTED_RE = re.compile(rf"\b(?:{SPEECH_VERB_PATTERN})\s+({NAME_PATTERN})\b", re.I)
TAG_AFTER_RE = re.compile(rf"\b({NAME_PATTERN})\s+(?:{SPEECH_VERB_PATTERN})\b", re.I)
TAG_BEFORE_RE = re.compile(rf"\b(?:{SPEECH_VERB_PATTERN})\b[^.!?]{{0,30}}$", re.I)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[\w’'\-]+")

STOP_NAMES = {
    "a",
    "after",
    "adding",
    "all",
    "almost",
    "also",
    "although",
    "an",
    "and",
    "another",
    "answering",
    "any",
    "anyone",
    "anything",
    "as",
    "asking",
    "at",
    "because",
    "before",
    "both",
    "but",
    "by",
    "calling",
    "chuckling",
    "closing",
    "continuing",
    "deciding",
    "prepare",
    "immediately",
    "damn",
    "dropping",
    "each",
    "either",
    "enough",
    "even",
    "eventually",
    "every",
    "everyone",
    "everything",
    "feeling",
    "finally",
    "first",
    "for",
    "frowning",
    "from",
    "glancing",
    "grinning",
    "growling",
    "he",
    "hearing",
    "her",
    "here",
    "hissing",
    "his",
    "holding",
    "how",
    "however",
    "i",
    "if",
    "in",
    "instead",
    "within",
    "during",
    "between",
    "among",
    "against",
    "towards",
    "toward",
    "through",
    "over",
    "down",
    "around",
    "along",
    "across",
    "beyond",
    "behind",
    "below",
    "above",
    "outside",
    "inside",
    "it",
    "its",
    "just",
    "knowing",
    "last",
    "leaning",
    "later",
    "laughing",
    "like",
    "least",
    "less",
    "listening",
    "looking",
    "lowering",
    "many",
    "maybe",
    "meanwhile",
    "more",
    "most",
    "moving",
    "much",
    "muttering",
    "neither",
    "next",
    "no",
    "nobody",
    "nodding",
    "nor",
    "not",
    "noticing",
    "now",
    "of",
    "on",
    "once",
    "one",
    "only",
    "opening",
    "or",
    "other",
    "others",
    "otherwise",
    "perhaps",
    "pulling",
    "pushing",
    "raising",
    "reaching",
    "realizing",
    "really",
    "remembering",
    "replying",
    "responding",
    "saying",
    "seeing",
    "shaking",
    "she",
    "shouting",
    "shrugging",
    "sighing",
    "since",
    "sitting",
    "smiling",
    "slowly",
    "so",
    "some",
    "someone",
    "something",
    "soon",
    "speaking",
    "standing",
    "staring",
    "starting",
    "stepping",
    "still",
    "stopping",
    "suddenly",
    "taking",
    "than",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "thinking",
    "this",
    "those",
    "though",
    "three",
    "to",
    "too",
    "trying",
    "turning",
    "two",
    "unless",
    "until",
    "very",
    "waiting",
    "walking",
    "was",
    "watching",
    "we",
    "well",
    "what",
    "when",
    "whether",
    "which",
    "while",
    "whispering",
    "who",
    "why",
    "with",
    "without",
    "wondering",
    "yet",
    "you",
}

HONORIFICS = {
    "captain",
    "dreamer",
    "duke",
    "duchess",
    "elder",
    "general",
    "king",
    "lady",
    "lord",
    "madam",
    "master",
    "princess",
    "queen",
    "saint",
    "sir",
    "sovereign",
    "supreme",
}

ALIASES = {
    "sunless": "Sunless",
    "sunny": "Sunless",
    "master sunless": "Sunless",
    "lord sunless": "Sunless",
    "dreamer sunless": "Sunless",
    "supreme sunless": "Sunless",
    "lord of shadows": "Sunless",
    "the lord of shadows": "Sunless",
    "shadow slave": "Sunless",
    "lost from light": "Sunless",
    "sovereign of death": "Sunless",
    "the sovereign of death": "Sunless",
    "neph": "Nephis",
    "nephis": "Nephis",
    "changing star": "Nephis",
    "princess nephis": "Nephis",
    "lady nephis": "Nephis",
    "cassie": "Cassie",
    "cassia": "Cassie",
    "saint cassia": "Cassie",
    "effie": "Effie",
    "saint effie": "Effie",
    "kai": "Kai",
    "nightingale": "Kai",
    "jet": "Jet",
    "master jet": "Jet",
    "soul reaper": "Jet",
    "rain": "Rain",
    "morgan": "Morgan",
    "mordret": "Mordret",
    "prince of nothing": "Mordret",
    "the prince of nothing": "Mordret",
    "jest": "Jest",
    "noctis": "Noctis",
    "ananke": "Ananke",
    "seishan": "Seishan",
    "asterion": "Asterion",
    "eurys": "Eurys",
    "ki song": "Ki Song",
    "tamar": "Tamar",
    "naeve": "Naeve",
    "caster": "Caster",
    "solace": "Solace",
}

NON_CHARACTER_NAMES = {
    "attribute",
    "ascended",
    "awakened",
    "dream realm",
    "dreamer",
    "echo",
    "enchantment description",
    "fire keepers",
    "flaw",
    "legacy",
    "memory",
    "nightmare",
    "nightmare creature",
    "nightmare spell",
    "rank",
    "sleeper",
    "soul core",
    "spell",
    "the blind girl",
    "the dream realm",
    "the nightmare spell",
    "the old man",
    "the spell",
}

CHAPTER_SKIP_TERMS = {
    "cover",
    "copyright",
    "table of contents",
    "title page",
}

VOLUME_RE = re.compile(
    r"^Shadow Slave\s*-\s*Vol(?:ume)?\.?\s*(\d+)\s*-\s*(.*)$",
    re.I,
)


@dataclass(frozen=True)
class QuoteSpan:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ExtractedQuote:
    character: str
    character_raw: str
    quote: str
    word_count: int
    char_count: int
    volume: int
    volume_title: str
    chapter: str
    chapter_index: int
    quote_index: int
    source_file: str
    confidence: str


def volume_info(path: Path) -> tuple[int, str]:
    name = path.stem
    match = VOLUME_RE.match(name)
    if not match:
        return 0, name
    return int(match.group(1)), match.group(2).strip()


def _clean_fragment(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = value.replace("\u00ad", "").replace("\u200b", "").replace("\ufeff", "")
    return SPACE_RE.sub(" ", value).strip()


def _document_title(raw: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
    if not match:
        return ""
    title = _clean_fragment(match.group(1))
    return "" if title.lower() == "unknown" else title


def _iter_chapters(raw: str, fallback_title: str = "") -> Iterator[tuple[str, list[str]]]:
    pattern = re.compile(r"<(h1|h2|h3|p)[^>]*>(.*?)</\1>", re.S | re.I)
    tokens = [
        (match.group(1).lower(), _clean_fragment(match.group(2)))
        for match in pattern.finditer(raw)
    ]
    tokens = [(tag, text) for tag, text in tokens if text]
    if not tokens:
        return

    h1_count = sum(1 for tag, _ in tokens if tag == "h1")
    if h1_count:
        chapter = ""
        blocks: list[str] = []
        for tag, text in tokens:
            if tag == "h1":
                if blocks and chapter:
                    yield chapter, blocks
                chapter = text
                blocks = []
            elif tag == "p" and chapter:
                blocks.append(text)
        if chapter and blocks:
            yield chapter, blocks
        return

    chapter = next((text for tag, text in tokens if tag in {"h2", "h3"}), "")
    if not chapter:
        chapter = _document_title(raw) or fallback_title
    blocks = [text for tag, text in tokens if tag == "p"]
    if chapter and blocks:
        yield chapter, blocks


def _single_quote_spans(text: str) -> list[QuoteSpan]:
    marks: list[tuple[int, str]] = []
    for index, char in enumerate(text):
        if char not in {"'", "‘", "’"}:
            continue
        previous = text[index - 1] if index else ""
        following = text[index + 1] if index + 1 < len(text) else ""
        if char == "‘":
            marks.append((index, "open"))
            continue
        if char == "’":
            if previous and following and previous.isalnum() and following.isalnum():
                continue
            marks.append((index, "close"))
            continue
        if previous and following and previous.isalnum() and following.isalnum():
            continue
        if not previous or previous.isspace() or previous in "([{—–-.,;:!?":
            if following and not following.isspace():
                marks.append((index, "open"))
                continue
        if not following or following.isspace() or following in ")]}—–-.,;:!?":
            marks.append((index, "close"))

    stack: list[int] = []
    spans: list[QuoteSpan] = []
    for index, kind in marks:
        if kind == "open":
            stack.append(index)
            continue
        if not stack:
            continue
        start = stack.pop()
        inner = text[start + 1 : index]
        if 2 <= len(inner) <= 400:
            spans.append(QuoteSpan(start, index + 1, inner))
    return spans


def quote_spans(text: str) -> list[QuoteSpan]:
    spans: list[QuoteSpan] = []
    for pattern in (
        re.compile(r"“([^”]{2,400})”"),
        re.compile(r'"([^"]{2,400})"'),
        re.compile(r"‘([^’]{2,400})’"),
    ):
        for match in pattern.finditer(text):
            spans.append(QuoteSpan(match.start(), match.end(), match.group(1)))
    spans.extend(_single_quote_spans(text))
    spans.sort(key=lambda span: (span.start, -(span.end - span.start)))

    kept: list[QuoteSpan] = []
    for span in spans:
        if any(span.start >= outer.start and span.end <= outer.end for outer in kept):
            continue
        kept.append(span)
    return sorted(kept, key=lambda span: span.start)


def _first_sentence(text: str) -> str:
    return SENTENCE_SPLIT_RE.split(text.strip(), maxsplit=1)[0]


def _last_sentence(text: str) -> str:
    parts = [part for part in SENTENCE_SPLIT_RE.split(text.strip()) if part]
    return parts[-1] if parts else ""


def _name_candidates(text: str) -> list[str]:
    names: list[str] = []
    for match in NAME_RE.finditer(text):
        value = match.group(0).strip()
        lower = value.lower()
        first = lower.split()[0]
        if lower in STOP_NAMES:
            continue
        if lower in NON_CHARACTER_NAMES:
            continue
        if first in STOP_NAMES and first != "the":
            continue
        if value not in names:
            names.append(value)
    return names


def canonical_character(name: str) -> str | None:
    value = SPACE_RE.sub(" ", name).strip().strip(",.;:!?")
    value = re.sub(r"['’]s$", "", value, flags=re.I).strip()
    if not value:
        return None

    alias = ALIASES.get(value.lower())
    if alias:
        return alias

    parts = value.split()
    while parts and parts[0].lower() in HONORIFICS:
        parts.pop(0)
    if not parts:
        return None
    value = " ".join(parts)
    alias = ALIASES.get(value.lower())
    if alias:
        return alias
    parts = value.split()
    if parts and parts[0].lower() in STOP_NAMES and parts[0].lower() != "the":
        return None
    if value.lower() in STOP_NAMES or value.lower() in NON_CHARACTER_NAMES:
        return None
    if len(value) > 40 or not re.search(r"[A-Za-z]", value):
        return None
    return value


def _tag_from_after(text: str) -> str | None:
    if not text.strip():
        return None
    sentence = _first_sentence(text)
    match = TAG_AFTER_INVERTED_RE.search(sentence)
    if match:
        return match.group(1)
    match = TAG_AFTER_RE.search(sentence)
    if match:
        return match.group(1)
    return None


def _tag_from_before(text: str) -> str | None:
    sentence = _last_sentence(text)
    if not TAG_BEFORE_RE.search(sentence):
        return None
    names = _name_candidates(sentence)
    return names[0] if names else None


def _action_from_before(text: str) -> str | None:
    sentence = _last_sentence(text)
    if len(sentence) > 200 or not re.match(rf"^{NAME_PATTERN}\b", sentence):
        return None
    names = _name_candidates(sentence)
    if len(names) == 1:
        return names[0]
    return None


def _speaker_from_previous(previous: str) -> str | None:
    if not previous or quote_spans(previous):
        return None
    sentence = _last_sentence(previous)
    if TAG_BEFORE_RE.search(sentence):
        names = _name_candidates(sentence)
        if names:
            return names[0]
    if len(previous) > 140 or not re.match(rf"^{NAME_PATTERN}\b", sentence):
        return None
    names = _name_candidates(sentence)
    if len(names) == 1:
        return names[0]
    return None


def _speaker_from_next(following: str) -> str | None:
    if not following or quote_spans(following):
        return None
    sentence = _first_sentence(following)
    match = TAG_AFTER_INVERTED_RE.match(sentence)
    if match:
        return match.group(1)
    match = TAG_AFTER_RE.match(sentence)
    if match:
        return match.group(1)
    return None


def _quote_is_usable(text: str) -> bool:
    if not 12 <= len(text) <= 360:
        return False
    if len(WORD_RE.findall(text)) < 3:
        return False
    if not re.search(r"[A-Za-z]", text):
        return False
    if text.startswith("[") or text.endswith("]"):
        return False
    if "\ufffd" in text:
        return False
    return True


def _clean_quote(text: str) -> str:
    value = SPACE_RE.sub(" ", text).strip()
    value = value.strip("“”")
    return value


def _iter_quotes(
    chapter: str,
    chapter_index: int,
    blocks: list[str],
    volume: int,
    volume_title: str,
    source_file: str,
    quote_index: int,
) -> Iterator[ExtractedQuote]:
    for block_index, block in enumerate(blocks):
        if block.startswith("[") and block.endswith("]"):
            continue
        spans = quote_spans(block)
        if not spans:
            continue

        previous = blocks[block_index - 1] if block_index else ""
        following = blocks[block_index + 1] if block_index + 1 < len(blocks) else ""
        for span_index, span in enumerate(spans):
            next_start = spans[span_index + 1].start if span_index + 1 < len(spans) else len(block)
            before = block[: span.start]
            after = block[span.end : next_start]
            if not after.strip() and span_index + 1 == len(spans):
                after = block[span.end :]

            speaker = _tag_from_after(after)
            confidence = "tag"
            if not speaker:
                speaker = _tag_from_before(before)
            if not speaker:
                speaker = _action_from_before(before)
                if speaker:
                    confidence = "action"
            if not speaker:
                speaker = _speaker_from_previous(previous)
                confidence = "tag"
            if not speaker:
                speaker = _speaker_from_next(following)
            if not speaker:
                continue

            quote = _clean_quote(span.text)
            if not _quote_is_usable(quote):
                continue
            character = canonical_character(speaker)
            if not character:
                continue

            quote_index += 1
            yield ExtractedQuote(
                character=character,
                character_raw=speaker,
                quote=quote,
                word_count=len(WORD_RE.findall(quote)),
                char_count=len(quote),
                volume=volume,
                volume_title=volume_title,
                chapter=chapter,
                chapter_index=chapter_index,
                quote_index=quote_index,
                source_file=source_file,
                confidence=confidence,
            )


def extract_quotes_from_epub(path: Path) -> list[ExtractedQuote]:
    volume, volume_title = volume_info(path)
    quotes: list[ExtractedQuote] = []
    quote_index = 0
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.lower().endswith((".xhtml", ".html", ".htm"))
        )
        for name in names:
            raw = archive.read(name).decode("utf-8", "replace")
            fallback_title = Path(name).stem
            for chapter_index, (chapter, blocks) in enumerate(
                _iter_chapters(raw, fallback_title), start=1
            ):
                if chapter.strip().lower() in CHAPTER_SKIP_TERMS:
                    continue
                extracted = list(
                    _iter_quotes(
                        chapter,
                        chapter_index,
                        blocks,
                        volume,
                        volume_title,
                        name,
                        quote_index,
                    )
                )
                quotes.extend(extracted)
                if extracted:
                    quote_index = extracted[-1].quote_index
    return quotes


def iter_epubs(directory: Path) -> Iterator[Path]:
    yield from sorted(directory.glob("*.epub"), key=lambda path: volume_info(path)[0])
