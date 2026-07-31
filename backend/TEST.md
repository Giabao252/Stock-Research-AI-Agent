# Testing Guide (LOCAL)

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

1. FastMCP server running:
```bash
fastmcp run app/mcp_servers/server.py --transport http --port 8001
```

2. Ingest run

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

3. run_analysis() on AAPL
```bash
.venv/bin/python -c "
import asyncio
from app.agent.runner import run_analysis

async def main():
    async for event in run_analysis('AAPL'):
        print(f'[{event.type}]', event.model_dump(exclude={'type'}))

asyncio.run(main())
" 2>&1
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

Writing this suite, and running it, surfaced seven real bugs — worth remembering when deciding whether a "just write tests" pass, or an actual live run, is worth the time:

1. `code_tool.py` read the wrong PrintCollector object/attribute, so `stdout_output` failed Pydantic validation on every call.
2. `code_tool.py` was missing `_getitem_` in its restricted globals, so `context['key']` — the tool's own documented usage example — failed outright.
3. `clients/qdrant.py` called `_client.search()`, which doesn't exist in the installed `qdrant-client` version (renamed `query_points()`, different response shape). This broke all of RAG retrieval.
4. `clients/qdrant.py` never created payload indexes, and Qdrant Cloud's strict mode rejects filtering on an unindexed field. Fixed by making index creation part of `init_collections()`, idempotently, so it self-heals collections created before the fix existed.
5. `code_tool.py` constructed `ExecutionResult(result=result, ...)` outside any try/except, so a non-scalar `result` (a dict, say — a very natural thing for the agent to try when computing several metrics at once) raised an uncaught `pydantic.ValidationError` straight through the MCP layer instead of a clean typed error.
6. The citation-groundedness check (`agent/hooks.py`'s `citation_tracker`) only tracked *which chunk_ids were seen*, not *which source_url each one actually had*. A live run showed the model reusing a real, previously-seen filing chunk_id but pairing it with a fabricated external URL for a claim that actually came from `web_search_tool` — passing the old check while citing a source that was never retrieved. Fixed by tracking `(chunk_id → real source_url)` pairs and a separate seen-URLs set for news claims, and making `Claim.chunk_id` optional (`None` for web-search-derived claims, since `NewsResult` has no chunk to point to).
7. The fix for #6 shipped with a bug of its own, caught immediately by the very next live run: `agent/hooks.py`'s `PostToolUse` hook assumed `tool_response` was a plain dict, but the real SDK delivers it as a JSON-encoded *string* with the payload nested one level under a `"result"` key (confirmed by capturing a raw hook call against the live server — nothing in the SDK's type stubs documents this, `tool_response` is typed as `Any`). Every mocked test had only ever exercised the assumed shape, so `chunk_sources`/`seen_urls` were silently always empty, and the live run showed *every single claim* in the report — including correctly-cited ones — flagged as ungrounded. Fixed with a `_parse_tool_response` normalization step (JSON-decode if string, unwrap `"result"` if present) that both plain-dict built-in tools and JSON-string MCP tools now go through.

Tier 1/2 mocks caught bugs 1, 2, and 5 by exercising real call shapes and non-happy-path inputs. Bugs 3, 4, 6, and 7 only surfaced because of actual Tier 3 live runs — mocks alone would have kept asserting against the wrong API, or the wrong notion of "grounded," or the wrong wire shape, indefinitely. #7 in particular is the sharpest example in this whole list: a mocked test can only ever verify code against the shape you *assumed* — it takes a real run to find out the assumption itself was wrong.
