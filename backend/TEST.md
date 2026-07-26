# Testing Guide

Three tiers. Tier 1 and Tier 2 are what `pytest` runs — fully mocked, free, safe for CI. Tier 3 is manual, costs real API money, and has no pytest file at all.

| Tier | Location | What it hits | Runs in CI |
|---|---|---|---|
| 1 — Unit | `tests/unit/` | Nothing external — every client/tool/SDK call is mocked | Yes |
| 2 — MCP wiring | `tests/integration/` | Real MCP protocol layer via `fastmcp.Client(mcp)`, in-process; external APIs still mocked | Yes |
| 3 — Live end-to-end | manual only, no test file | Real EDGAR, OpenAI, Qdrant Cloud, Upstash Redis, Anthropic | No |

## Setup

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # requirements.txt + pytest + pytest-asyncio
```

## Running the tests

```bash
# everything (Tier 1 + Tier 2)
.venv/bin/python -m pytest tests/ -q

# one tier at a time
.venv/bin/python -m pytest tests/unit -q
.venv/bin/python -m pytest tests/integration -q
```

Useful flags for local dev:

```bash
.venv/bin/python -m pytest tests/ -q -x                    # stop at first failure
.venv/bin/python -m pytest tests/ -q -k "runner"            # filter by test name
.venv/bin/python -m pytest tests/unit/test_runner.py -v     # one file, verbose
.venv/bin/python -m pytest tests/ --collect-only -q         # list tests without running them
```

## What's not run automatically

Tier 3 — a live `run_analysis("AAPL")` run, or a live `ingest_ticker("AAPL")` against real Qdrant Cloud — is deliberately not a pytest file. It costs real API money and depends on live credentials in `.env`. Run it by hand when you need to verify real behavior, e.g.:

```bash
.venv/bin/python -c "
import asyncio
from app.clients.qdrant import init_collections
from app.rag.ingest import ingest_ticker

async def main():
    await init_collections()
    total = await ingest_ticker('AAPL', limit=1)
    print(f'chunks upserted: {total}')

asyncio.run(main())
"
```

## CI/CD (Phase 7)

The test step in `.github/workflows/ci.yml` is just:

```yaml
- name: Install dependencies
  run: |
    cd backend
    pip install -r requirements-dev.txt

- name: Run unit + integration tests
  run: |
    cd backend
    python -m pytest tests/ -q
```

No secrets required for this step — Tier 1 and Tier 2 never touch real credentials, so it can run on every PR, including from forks. The DeepEval golden-dataset eval (Phase 8) is a separate step that does need real API keys.

## Test file inventory

**`tests/unit/`** — one file per module, external calls mocked at the point they're imported into the module under test (e.g. `app.rag.retrieval.qdrant_client.query_dense`, not `app.clients.qdrant.query_dense`):

- `test_chunker.py`, `test_embedder.py`, `test_ingest.py`, `test_retrieval.py` — RAG pipeline
- `test_edgar_client.py`, `test_cohere_client.py`, `test_tavily_client.py`, `test_alpha_vantage_client.py`, `test_qdrant_client.py`, `test_redis_client.py` — HTTP/DB clients
- `test_rag_tool.py`, `test_edgar_tool.py`, `test_stock_tool.py`, `test_search_tool.py`, `test_code_tool.py` — MCP tools
- `test_hooks.py`, `test_prompts.py`, `test_runner.py` — Agent SDK wiring
- `test_models.py` — Pydantic schema regression guards
- `test_main.py` — FastAPI app

**`tests/integration/`**:

- `test_mcp_wiring.py` — the composed MCP server via `fastmcp.Client(mcp)`, in-process (no live HTTP server needed)

## A note on what these tests already caught

Writing this suite surfaced four real bugs before they hit a live run — worth remembering when deciding whether a "just write tests" pass is worth the time:

1. `code_tool.py` read the wrong PrintCollector object/attribute, so `stdout_output` failed Pydantic validation on every call.
2. `code_tool.py` was missing `_getitem_` in its restricted globals, so `context['key']` — the tool's own documented usage example — failed outright.
3. `clients/qdrant.py` called `_client.search()`, which doesn't exist in the installed `qdrant-client` version (renamed `query_points()`, different response shape). This broke all of RAG retrieval.
4. `clients/qdrant.py` never created payload indexes, and Qdrant Cloud's strict mode rejects filtering on an unindexed field. Fixed by making index creation part of `init_collections()`, idempotently, so it self-heals collections created before the fix existed.

Tier 1/2 mocks caught the first two by exercising real call shapes. The fourth only surfaced because of an actual Tier 3 live run — mocks alone would have kept asserting against the wrong API indefinitely.
