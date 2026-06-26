"""
Pydantic model for a single text chunk produced by the ingestion pipeline.
No internal app imports.
"""
from pydantic import BaseModel

class Chunk(BaseModel):
    chunk_id: str       # sha256(ticker:year:section:idx)[:16] — stable across re-ingests
    text: str           # raw chunk text, up to 512 tokens
    ticker: str         # e.g. "AAPL"
    section: str        # 10-K section label, e.g. "Item 1A"
    year: int           # filing year, e.g. 2024
    source_url: str     # SEC archive URL the raw doc was fetched from
    score: float = 0.0  # retrieval score; 0.0 at ingestion time, set by retrieval.py
