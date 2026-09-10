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

## Tier 4 — API route testing (manual, server must be running)

Tests the full HTTP layer: gateway, agent SSE stream, and reports endpoints.
Requires the FastAPI server and the FastMCP server both running locally, and a
populated `.env`.

---

### Chained test sequence (Swagger UI + curl)

Three self-contained scenarios. Each scenario produces values used by later
steps in the same scenario — copy them as you go. The SSE stream step in
Scenario A is the only one that can't run in Swagger UI; everything else can.

**Which tool for which endpoint:**

| Endpoint | Swagger UI | curl |
|---|---|---|
| `GET /health` | ✅ | ✅ |
| `POST /analyze` | ✅ | ✅ |
| `GET /sessions/{id}/stream` | ❌ can't stream | ✅ required |
| `POST /ask` | ✅ | ✅ |
| `DELETE /sessions/{id}` | ✅ | ✅ |
| `GET /reports` | ✅ | ✅ |
| `GET /reports/{id}` | ✅ | ✅ |
| `GET /chunks/{id}` | ✅ | ✅ |

---

#### Scenario A — Golden path (AAPL analysis → read report → read chunk)

Tests: `GET /health` → `POST /analyze` → SSE stream → `GET /reports` → `GET /reports/{id}` → `GET /chunks/{id}`

---

**Step A-1 · GET /health** *(Swagger UI)*

No parameters. Click **Try it out → Execute**.

Expected response body:
```json
{"status": "ok", "model": "haiku"}
```

If this fails, the FastAPI server isn't running. Stop here and fix startup.

---

**Step A-2 · POST /analyze** *(Swagger UI)*

Request body:
```json
{"ticker": "AAPL"}
```

Expected response (`202`):
```json
{
  "session_id": "________-____-____-____-____________",
  "ticker": "AAPL"
}
```

📋 **Copy `session_id` → call it `{{SESSION_ID}}`**. You'll use it in A-3 and A-4.
Note: `report_id` (from the done event) will equal this same value.

---

**Step A-3 · GET /sessions/{session_id}/stream** *(curl only — Swagger UI cannot stream SSE)*

```bash
curl -N "http://localhost:8000/sessions/{{SESSION_ID}}/stream"
```

Replace `{{SESSION_ID}}` with the value from A-2. Leave this terminal open — the
agent run takes 30–120 seconds depending on whether AAPL is already ingested.

Watch for this sequence of event types:
```
data: {"type":"thought", ...}
data: {"type":"tool_call","tool":"stock_data_tool", ...}
data: {"type":"observe","summary":"stock_data_tool returned StockMetrics"}
data: {"type":"tool_call","tool":"rag_retrieval_tool", ...}
data: {"type":"observe","summary":"rag_retrieval_tool returned 5 chunk(s)"}
data: {"type":"tool_call","tool":"web_search_tool", ...}
data: {"type":"observe","summary":"web_search_tool returned 5 result(s)"}
data: {"type":"done","report_id":"{{SESSION_ID}}"}
```

📋 **Wait for the `done` event before continuing to A-4.**
`report_id` in the done event equals `{{SESSION_ID}}` — they are the same value.

---

**Step A-4 · GET /reports** *(Swagger UI)*

Parameters:
```
ticker  = AAPL
limit   = 10
```

Expected response (`200`): a JSON array with at least one entry. Find the entry
whose `generated_at` matches your run timestamp. Confirm these fields are present:
- `verdict`: one of `"bullish"` / `"bearish"` / `"neutral"`
- `confidence`: a float between `0.0` and `1.0`
- `bull_case`: non-empty array of Claim objects
- `metrics`: object with `pe_ratio`, `market_cap`, `revenue_ttm`
- `partial`: `false` (ideally — if `true`, `partial_reason` explains the gap)

---

**Step A-5 · GET /reports/{report_id}** *(Swagger UI)*

Parameters:
```
report_id = {{SESSION_ID}}
```

Expected response (`200`): the same single `ResearchReport` object.

📋 **From `bull_case[0].chunk_id`, copy the value → call it `{{CHUNK_ID}}`.**
Skip to A-6. If `chunk_id` is `null` on the first claim, that claim came from
`web_search_tool` — use the next claim in `bull_case` or try `bear_case` instead.

---

**Step A-6 · GET /chunks/{chunk_id}** *(Swagger UI)*

Parameters:
```
chunk_id = {{CHUNK_ID}}
```

Expected response (`200`):
```json
{
  "chunk_id": "{{CHUNK_ID}}",
  "text": "...(raw 10-K passage)...",
  "ticker": "AAPL",
  "section": "Item 7",
  "year": 2024,
  "source_url": "https://www.sec.gov/Archives/edgar/...",
  "score": 0.0
}
```

This is the exact passage from the SEC filing that backs the `bull_case[0]` claim.
The `source_url` should match `bull_case[0].source_url` in the report from A-5.

---

#### Scenario B — Follow-up Q&A (MSFT)

Tests: `POST /analyze` → `POST /ask`

The `/ask` endpoint needs a live Redis session. The trick: a session exists in Redis
from the moment `POST /analyze` returns until the SSE stream completes. So you can
call `/ask` immediately after `/analyze` — before opening the stream — and it works.

---

**Step B-1 · POST /analyze** *(Swagger UI)*

Request body:
```json
{"ticker": "MSFT"}
```

📋 **Copy `session_id` → call it `{{SESSION_ID_B}}`.**

---

**Step B-2 · POST /ask** *(Swagger UI — do this immediately, before opening the stream)*

Request body:
```json
{
  "question": "What is MSFT's current P/E ratio and how does it compare to its 5-year average?",
  "ticker": "MSFT",
  "session_id": "{{SESSION_ID_B}}"
}
```

Expected response (`200`):
```json
{
  "text": "Microsoft's current P/E ratio is ...",
  "sources": [
    {
      "text": "...",
      "chunk_id": "...",
      "source_url": "https://...",
      "doc_name": "MSFT 10-K 2024"
    }
  ]
}
```

`sources` may be empty if the agent answered purely from `stock_data_tool` (which
has no chunk_id). That's valid — `chunk_id` is `null` for web/stock-derived sources.

After verifying the response, open the stream in a terminal to finish the session:
```bash
curl -N "http://localhost:8000/sessions/{{SESSION_ID_B}}/stream"
```

---

#### Scenario C — Session cancellation (NVDA)

Tests: `POST /analyze` → `DELETE /sessions/{id}`

Verifies the cleanup path — what happens when the user navigates away before the
stream finishes.

---

**Step C-1 · POST /analyze** *(Swagger UI)*

Request body:
```json
{"ticker": "NVDA"}
```

📋 **Copy `session_id` → call it `{{SESSION_ID_C}}`.**

---

**Step C-2 · DELETE /sessions/{session_id}** *(Swagger UI)*

Parameters:
```
session_id = {{SESSION_ID_C}}
```

Expected response: `204 No Content` (empty body).

---

**Step C-3 · GET /reports/{report_id}** *(Swagger UI — verifies session was cleaned up)*

Parameters:
```
report_id = {{SESSION_ID_C}}
```

Expected response: `404 Not Found`
```json
{"detail": "Report '{{SESSION_ID_C}}' not found"}
```

This confirms the session was deleted before the agent ran — no orphan report in
Qdrant. If you get `200`, the agent somehow ran before the DELETE reached Redis.

---

**Step C-4 · DELETE /sessions/{session_id} again** *(Swagger UI — idempotency check)*

Parameters:
```
session_id = {{SESSION_ID_C}}
```

Expected response: `204 No Content` again — not a `404`.
DELETE must be idempotent so the frontend can call it safely on unmount without
checking whether the session still exists.

---

### Prerequisites

**Terminal 1 — MCP server** (the agent calls this for tools):
```bash
cd backend
set -a && source .env && set +a
PYTHONPATH=. fastmcp run app/mcp_servers/server.py --transport http --port 8001
```

**Terminal 2 — FastAPI backend**:
```bash
cd backend
set -a && source .env && set +a
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8000
```

Verify startup: the uvicorn log should print `Application startup complete.` and
Qdrant should log `Created collection filings` / `Created collection reports`
(or nothing if they already exist — `init_collections` is idempotent).

---

### GET /health

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "ok", "model": "haiku"}
```

---

### POST /analyze

Creates a session and returns the `session_id`. The agent does **not** start yet —
it starts when the SSE connection opens.

```bash
curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}' | python3 -m json.tool
```

Expected (session_id will differ):
```json
{
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "ticker": "AAPL"
}
```

Save the `session_id` for the next two steps:
```bash
SESSION_ID=$(curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Session: $SESSION_ID"
```

---

### GET /sessions/{session_id}/stream  ← the main event

Opens the SSE connection and starts the agent. Events stream until a `done` or
`error` event. Use `curl -N` (no buffering) so chunks print immediately:

```bash
curl -N "http://localhost:8000/sessions/$SESSION_ID/stream"
```

Expected output (one `data:` line per event, \n\n between each):
```
data: {"type":"thought","content":"I'll start by fetching live stock data for AAPL..."}

data: {"type":"tool_call","tool":"stock_data_tool","args":{"ticker":"AAPL"}}

data: {"type":"observe","summary":"stock_data_tool returned StockMetrics"}

data: {"type":"tool_call","tool":"rag_retrieval_tool","args":{"query":"Apple revenue growth","ticker":"AAPL","top_k":5}}

data: {"type":"observe","summary":"rag_retrieval_tool returned 5 chunk(s)"}

data: {"type":"done","report_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6"}
```

On `done`, the report has been persisted to Qdrant and the Redis session is cleared.
On `error`, check the FastAPI terminal for the traceback — common causes: MCP server
not running, or `ANTHROPIC_API_KEY` not in `.env`.

---

### POST /ask  (follow-up question)

Only works while a session is **still in Redis** — i.e. either the stream is still
running or you re-created the session before it expired. The easiest test is to
start a new session and ask before the stream finishes:

```bash
# In one terminal, start a slow stream:
SESSION_ID=$(curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

curl -N "http://localhost:8000/sessions/$SESSION_ID/stream" &

# In another terminal, ask a follow-up while the stream is live:
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is MSFT's P/E ratio?\", \"ticker\": \"MSFT\", \"session_id\": \"$SESSION_ID\"}" \
  | python3 -m json.tool
```

Expected shape:
```json
{
    "text": "Microsoft's P/E ratio as of the latest data is ...",
    "sources": [
        {
            "text": "...",
            "chunk_id": "a1b2c3d4e5f6a7b8",
            "source_url": "https://...",
            "doc_name": "MSFT 10-K 2024"
        }
    ]
}
```

---

### DELETE /sessions/{session_id}

```bash
# Create a session, then immediately cancel it
SESSION_ID=$(curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "http://localhost:8000/sessions/$SESSION_ID"
# → 204

# Idempotent — deleting again still returns 204
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "http://localhost:8000/sessions/$SESSION_ID"
# → 204
```

---

### GET /reports?ticker=AAPL

Only returns results after at least one SSE stream has completed for this ticker
(the report is persisted on `done`).

```bash
curl -s "http://localhost:8000/reports?ticker=AAPL" | python3 -m json.tool
```

Expected: a JSON array of `ResearchReport` objects, ordered oldest-first.
Returns `[]` if no reports exist yet for this ticker.

Pagination:
```bash
curl -s "http://localhost:8000/reports?ticker=AAPL&limit=2"
```

---

### GET /reports/{report_id}

`report_id` is the `session_id` returned from the `done` SSE event.

```bash
# Run a full analysis first, grab the report_id from the done event:
REPORT_ID="<paste-report_id-from-done-event>"

curl -s "http://localhost:8000/reports/$REPORT_ID" | python3 -m json.tool
```

Expected: a single `ResearchReport` JSON object with `bull_case`, `bear_case`,
`verdict`, `confidence`, `metrics`, `tool_trace`, and `generated_at`.

---

### GET /chunks/{chunk_id}

`chunk_id` is a 16-char hex string from any `Claim.chunk_id` in a report.
This is what the frontend CitationDrawer uses to show the raw 10-K passage.

```bash
# Grab a chunk_id from a report's bull_case or bear_case:
CHUNK_ID=$(curl -s "http://localhost:8000/reports/$REPORT_ID" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['bull_case'][0]['chunk_id'])")

curl -s "http://localhost:8000/chunks/$CHUNK_ID" | python3 -m json.tool
```

Expected:
```json
{
    "chunk_id": "a1b2c3d4e5f6a7b8",
    "text": "Apple's revenue for fiscal year 2024 increased 6 percent ...",
    "ticker": "AAPL",
    "section": "Item 7",
    "year": 2024,
    "source_url": "https://www.sec.gov/Archives/edgar/data/...",
    "score": 0.0
}
```

404 if the chunk_id doesn't exist in Qdrant (e.g. a web-search-derived claim
where `chunk_id` is `null` in the report — don't pass those here).

---

### Interactive docs

All endpoints are also explorable at **http://localhost:8000/docs** (Swagger UI)
while the server is running. Useful for one-off manual tests without curl.

---

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
