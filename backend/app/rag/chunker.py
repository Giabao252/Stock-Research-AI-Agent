"""
Converts raw SEC 10-K bytes from edgar.py client into token-bounded Chunk objects.

Public API:
    chunk_filing(raw_bytes, ticker, year, source_url, *, chunk_size=512, overlap=50)
        -> list[Chunk]

Synchronous and CPU-bound — callers in ingest.py wrap this with asyncio.to_thread().
"""

import hashlib
import re
import warnings

import tiktoken
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.models.chunk import Chunk

# Matches 10-K section headers like "Item 1", "Item 1A.", "ITEM 7A"
_SECTION_RE = re.compile(
    r"(?im)^\s*Item\s+(\d+[A-Z]?)\b\.?\s*[.—–\-]?\s*(.{0,80})",
)

_MIN_CHUNK_TOKENS = 20


def _extract_text(raw_bytes: bytes) -> str:
    stripped = raw_bytes.lstrip()
    if stripped[:1] == b"<":
        # Modern SEC filings use iXBRL (inline XBRL), which looks like XML but is valid HTML. Suppress the spurious XMLParsedAsHTMLWarning.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(raw_bytes, "lxml")
        return soup.get_text(separator="\n", strip=True)
    return raw_bytes.decode("utf-8", errors="replace")


def _detect_sections(text: str) -> list[tuple[int, str]]:
    """Return list of (char_offset, section_label) sorted by position."""
    sections: list[tuple[int, str]] = []
    for m in _SECTION_RE.finditer(text):
        label = f"Item {m.group(1)}"
        sections.append((m.start(), label))

    if not sections:
        return [(0, "FULL")]

    # Deduplicate consecutive matches for the same item number (table of contents
    # often lists each item twice before the actual section body appears).
    # Keep only the last occurrence of each label so we get the body, not the TOC.
    seen: dict[str, int] = {}
    for offset, label in sections:
        seen[label] = offset
    return sorted((offset, label) for label, offset in seen.items())


def _make_chunk_id(ticker: str, year: int, section: str, idx: int) -> str:
    key = f"{ticker}:{year}:{section}:{idx}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def chunk_filing(
    raw_bytes: bytes,
    ticker: str,
    year: int,
    source_url: str,
    *,
    chunk_size: int = 512, #
    overlap: int = 50,
) -> list[Chunk]:
    """Parse raw 10-K bytes and return a list of token-bounded Chunk objects.

    Each chunk is at most `chunk_size` tokens with `overlap` tokens of context
    carried over from the previous chunk within the same section.
    """
    text = _extract_text(raw_bytes)
    sections = _detect_sections(text)

    enc = tiktoken.get_encoding("cl100k_base")
    stride = max(1, chunk_size - overlap)
    chunks: list[Chunk] = []
    chunk_index = 0

    # Pair each section with the start of the next to extract section text
    boundaries = sections + [(len(text), "END")]
    for (start, label), (next_start, _) in zip(boundaries, boundaries[1:]):
        section_text = text[start:next_start].strip()
        if not section_text:
            continue

        tokens = enc.encode(section_text)
        for i in range(0, max(1, len(tokens) - overlap), stride):
            window = tokens[i : i + chunk_size]
            if len(window) < _MIN_CHUNK_TOKENS:
                continue
            chunks.append(
                Chunk(
                    chunk_id=_make_chunk_id(ticker, year, label, chunk_index),
                    text=enc.decode(window),
                    ticker=ticker,
                    section=label,
                    year=year,
                    source_url=source_url,
                )
            )
            chunk_index += 1

    return chunks
