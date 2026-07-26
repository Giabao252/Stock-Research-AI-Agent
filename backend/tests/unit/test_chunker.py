"""
Unit tests for rag/chunker.py — pure functions, no network required.
"""

import pytest
from app.rag.chunker import chunk_filing, _detect_sections, _extract_text, _make_chunk_id

FAKE_10K_HTML = b"""
<html><body>
<p>Item 1. Business</p>
<p>Apple Inc. designs and sells consumer electronics and software.</p>
<p>Item 1A. Risk Factors</p>
<p>The company faces significant competition in all markets in which it operates.</p>
<p>Item 7. Management Discussion</p>
<p>Revenue increased 6 percent year-over-year driven by iPhone sales growth.</p>
</body></html>
"""

FAKE_10K_TEXT = b"""
Item 1. Business
Apple Inc. designs and sells consumer electronics and software.

Item 1A. Risk Factors
The company faces significant competition in all markets in which it operates.

Item 7. Management Discussion
Revenue increased 6 percent year-over-year driven by iPhone sales growth.
"""


def test_extract_text_strips_html():
    text = _extract_text(FAKE_10K_HTML)
    assert "<html>" not in text
    assert "Apple Inc." in text


def test_extract_text_passthrough_for_plaintext():
    text = _extract_text(FAKE_10K_TEXT)
    assert "Item 1A" in text
    assert "Risk Factors" in text


def test_detect_sections_finds_items():
    text = _extract_text(FAKE_10K_HTML)
    sections = _detect_sections(text)
    labels = [label for _, label in sections]
    assert "Item 1" in labels
    assert "Item 1A" in labels
    assert "Item 7" in labels


def test_detect_sections_fallback_on_no_items():
    sections = _detect_sections("No section headers here at all.")
    assert sections == [(0, "FULL")]


def test_chunk_filing_returns_chunks():
    chunks = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test")
    assert len(chunks) > 0


def test_chunk_filing_metadata():
    chunks = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test")
    for chunk in chunks:
        assert chunk.ticker == "AAPL"
        assert chunk.year == 2024
        assert chunk.source_url == "https://sec.gov/test"
        assert len(chunk.chunk_id) == 16
        assert len(chunk.text) > 0


def test_chunk_filing_respects_chunk_size():
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    chunks = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test", chunk_size=50)
    for chunk in chunks:
        assert len(enc.encode(chunk.text)) <= 50


def test_chunk_filing_sections_assigned():
    chunks = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test")
    sections = {chunk.section for chunk in chunks}
    assert sections.issubset({"Item 1", "Item 1A", "Item 7", "FULL"})


def test_chunk_ids_are_stable():
    chunks_a = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test")
    chunks_b = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test")
    assert [c.chunk_id for c in chunks_a] == [c.chunk_id for c in chunks_b]


def test_chunk_ids_differ_across_tickers():
    chunks_aapl = chunk_filing(FAKE_10K_HTML, ticker="AAPL", year=2024, source_url="https://sec.gov/test")
    chunks_msft = chunk_filing(FAKE_10K_HTML, ticker="MSFT", year=2024, source_url="https://sec.gov/test")
    ids_aapl = {c.chunk_id for c in chunks_aapl}
    ids_msft = {c.chunk_id for c in chunks_msft}
    assert ids_aapl.isdisjoint(ids_msft)


# ---------------------------------------------------------------------------
# _make_chunk_id
# ---------------------------------------------------------------------------

def test_make_chunk_id_is_deterministic():
    assert _make_chunk_id("AAPL", 2024, "Item 1A", 0) == _make_chunk_id("AAPL", 2024, "Item 1A", 0)


def test_make_chunk_id_differs_by_index():
    assert _make_chunk_id("AAPL", 2024, "Item 1A", 0) != _make_chunk_id("AAPL", 2024, "Item 1A", 1)


def test_make_chunk_id_is_16_hex_chars():
    chunk_id = _make_chunk_id("AAPL", 2024, "Item 1A", 0)
    assert len(chunk_id) == 16
    int(chunk_id, 16)  # raises ValueError if not valid hex


# ---------------------------------------------------------------------------
# _detect_sections — TOC dedup
# ---------------------------------------------------------------------------

def test_detect_sections_keeps_last_occurrence_of_duplicate_label():
    # table-of-contents style: "Item 1A" listed twice, body text starts at the second
    text = (
        "Item 1A. Risk Factors\n"
        "Item 1A. Risk Factors\n"
        "The real body text of risk factors goes here."
    )
    sections = _detect_sections(text)
    assert len(sections) == 1
    offset, label = sections[0]
    assert label == "Item 1A"
    assert offset == text.index("Item 1A", text.index("Item 1A") + 1)  # second occurrence


# ---------------------------------------------------------------------------
# chunk_filing — overlap, min-token filtering, empty input
# ---------------------------------------------------------------------------

def test_chunk_filing_custom_overlap_changes_chunk_count():
    long_html = b"<html><body><p>Item 1A. Risk Factors</p><p>" + b"risk factor sentence. " * 400 + b"</p></body></html>"
    chunks_low_overlap = chunk_filing(long_html, ticker="AAPL", year=2024, source_url="https://x", chunk_size=100, overlap=0)
    chunks_high_overlap = chunk_filing(long_html, ticker="AAPL", year=2024, source_url="https://x", chunk_size=100, overlap=80)
    # smaller stride (higher overlap) produces more, more-overlapping chunks over the same text
    assert len(chunks_high_overlap) > len(chunks_low_overlap)


def test_chunk_filing_drops_windows_below_min_chunk_tokens():
    # a short trailing section body well under _MIN_CHUNK_TOKENS should produce no chunk
    short_html = b"<html><body><p>Item 1A. Risk Factors</p><p>too short</p></body></html>"
    chunks = chunk_filing(short_html, ticker="AAPL", year=2024, source_url="https://x")
    assert chunks == []


def test_chunk_filing_empty_bytes_returns_empty_list():
    assert chunk_filing(b"", ticker="AAPL", year=2024, source_url="https://x") == []


def test_chunk_filing_whitespace_only_returns_empty_list():
    assert chunk_filing(b"   \n\n  ", ticker="AAPL", year=2024, source_url="https://x") == []
