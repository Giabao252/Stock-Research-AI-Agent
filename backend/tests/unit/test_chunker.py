"""
Unit tests for rag/chunker.py — pure functions, no network required.
"""

import pytest
from app.rag.chunker import chunk_filing, _detect_sections, _extract_text

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
