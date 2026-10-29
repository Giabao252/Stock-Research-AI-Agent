# StockBuddy — Agentic RAG Stock Research

An AI agent that researches a stock the way an analyst would: it pulls SEC filings, live financial data and recent news, then writes a **cited bull/bear report** while its reasoning streams live to the browser. Every claim links back to the exact source passage.

**Live demo:** https://stockbuddy-fe.vercel.app · **API docs:** https://stock-research-api-g8dp.onrender.com/docs

> If the API host has spun down from inactivity, the first request can be slow while it wakes up.

---

## What it does

- **Autonomous research.** Give it a ticker. The agent decides which tools to call (filings search, market data, news, calculations), observes the results and iterates until it can write a report.
- **Visible reasoning.** Thoughts, tool calls and observations stream to the UI over Server-Sent Events as they happen.
- **Grounded, cited output.** Reports are structured (`bull_case`, `bear_case`, `verdict`, `confidence`). Every claim carries a `chunk_id`, source URL and document name. Click a citation to open the raw passage with the supporting text highlighted.
- **Self-checking.** A post-tool hook tracks which sources the agent actually retrieved; claims without a retrieved source mark the report `partial` instead of passing silently.
- **Follow-ups, history, comparison.** Ask follow-up questions on a report, revisit past reports, diff two runs of the same ticker, or compare several tickers side by side. Reports export to Markdown / print.

## Architecture

```
Frontend (Vercel)  React + TypeScript + Tailwind + Vite + Zod
  └─ POST /analyze · GET /sessions/{id}/stream (SSE) · POST /ask · GET /reports/*

Backend (Render web service)  FastAPI + Pydantic
  ├─ Gateway router — session creation, health
  ├─ Agent router   — runs the Claude Agent SDK loop, translates hooks → SSE
  └─ Reports router — stored reports + citation chunks

MCP server (Render private service)  FastMCP, tools over HTTP
  ├─ rag_retrieval_tool  — BM25 + Qdrant dense → RRF → Cohere rerank
  ├─ stock_data_tool     — Alpha Vantage price / P/E / revenue (Redis-cached)
  ├─ web_search_tool     — Tavily news & analyst ratings
  ├─ edgar_fetch_tool    — on-demand 10-K ingestion for unseen tickers
  └─ code_execution_tool — RestrictedPython for ratio / growth maths

Managed services: Qdrant Cloud (filings + reports) · Upstash Redis (sessions, cache) · SEC EDGAR
```

### Design decisions worth a look

| Decision | Why |
|---|---|
| **`claude-agent-sdk`**, not the raw client | The SDK owns the tool loop, compaction and MCP wiring; the app owns persistence, SSE translation, stop conditions and the RAG pipeline. |
| **Hybrid retrieval** (BM25 ∥ dense → RRF → rerank) | Keyword search catches exact figures and names, dense search catches paraphrase; both run concurrently via `asyncio.gather`, fused with reciprocal rank fusion, then Cohere reranks top-20 → top-5. |
| **Section-aware chunking** of 10-Ks | Chunks respect filing sections (Risk Factors, MD&A…) so citations point at something meaningful and retrieval can filter by ticker + section. |
| **Server-owned metrics** | The model never writes numbers like P/E or market cap. The runner overwrites `metrics` with the real `stock_data_tool` payload, so figures can't be hallucinated. |
| **Agent tools run over MCP** | Tools are registered once on a FastMCP server with the `@tool` decorator, isolated from the agent process, with built-in WebSearch/WebFetch disabled so all evidence goes through citable tools. |
| **Cost & rate-limit control** | `max_budget_usd` cap per run; model tier is a config value (`CLAUDE_MODEL`); Alpha Vantage calls are throttled to its 1 req/s limit and cached 15 min in Redis; the API key is redacted from error text. |
| **Fetch-based SSE client** | The run starts when the stream opens, so `EventSource`'s auto-reconnect could silently start (and bill) a second run. The frontend reads the stream with `fetch` instead and never closes early. |
| **Typed end to end** | Pydantic models on the backend, mirrored by Zod schemas on the frontend; SSE events are a discriminated union that is exhaustively switched on. |
| **Strict module boundaries** | `clients/` and `models/` are leaf nodes that import nothing from the app; routers, agent, rag and MCP layers follow explicit import rules. |

### Stream contract

```ts
type StreamEvent =
  | { type: 'thought';   content: string }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { type: 'observe';   summary: string }
  | { type: 'done';      report_id: string }
  | { type: 'error';     message: string }
```

## Tech stack

**Backend:** Python 3.11, FastAPI, Pydantic v2, pydantic-settings, `claude-agent-sdk`, FastMCP, Qdrant, Upstash Redis, rank-bm25, Cohere rerank, OpenAI `text-embedding-3-small`, RestrictedPython, tenacity, pytest

**Frontend:** React 19, TypeScript (strict), Vite, Tailwind CSS v4 (no CSS files, no inline styles), Zod, React Router

**Infra:** Docker, GitHub Actions → GHCR, Render (Blueprint in [render.yaml](render.yaml)), Vercel

## Frontend architecture

Three layers with no business logic in components:

```
src/api/         fetch wrappers, Zod schemas, SSE reader
src/hooks/       all async + state logic (external stores, custom hooks)
src/components/  render only
src/pages/       Home · Report · History · ReportCompare · Compare
```

Live runs live in a global store, so you can navigate away mid-run and come back to the same stream. Untrusted model-written URLs are restricted to `http(s)` before they become links.

## Run it locally

Prerequisites: Python 3.11+, Node 22+, Docker, and accounts/keys for the services below.

```bash
# 1. Backend env: create backend/.env with the variables listed below

# 2. Backend + MCP server
docker compose up --build              # API on :8000, MCP on :8001

# 3. Frontend
cd frontend
cp .env.example .env.local             # VITE_API_BASE_URL=http://localhost:8000
npm ci
npm run dev                            # http://localhost:5173
```

Try the agent from a terminal:

```bash
curl -X POST localhost:8000/analyze -H 'content-type: application/json' \
  -d '{"ticker":"NVDA","session_id":"demo-1"}'
curl -N localhost:8000/sessions/demo-1/stream
```

### Environment variables (`backend/.env`)

| Variable | Used for |
|---|---|
| `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (default `haiku`) | Agent (API key only) |
| `OPENAI_API_KEY` | Embeddings |
| `QDRANT_URL`, `QDRANT_API_KEY` | Vector DB (Qdrant Cloud) |
| `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN` | Sessions + cache (read/write token) |
| `COHERE_API_KEY` | Reranker |
| `ALPHA_VANTAGE_KEY` | Market data |
| `TAVILY_API_KEY` | News search |
| `SEC_USER_NAME`, `SEC_USER_EMAIL` | EDGAR requires a contact identity |
| `MCP_SERVER_URL` | Where the agent reaches the MCP server |
| `CORS_ORIGINS` (JSON list), `CORS_ORIGIN_REGEX` | Allowed browser origins |

All configuration is read through `app/config.py`; nothing calls `os.getenv()` inline.

## Testing & CI

```bash
cd backend && pip install -r requirements-dev.txt && pytest tests -q   # 226 tests
cd frontend && npm run lint && npm run build                           # eslint + tsc + vite
```

GitHub Actions ([ci.yml](.github/workflows/ci.yml)) runs on every PR and push to `main`:

1. **test** — backend pytest suite
2. **frontend** — `npm ci`, ESLint, `tsc -b && vite build`
3. **docker** — builds the backend image; pushes to GHCR on `main`

## Deployment

- **Frontend → Vercel.** Root directory `frontend`, env `VITE_API_BASE_URL`. SPA rewrites in `vercel.json`.
- **Backend + MCP → Render** via the Blueprint in [render.yaml](render.yaml): a public web service plus a private service reachable only over Render's internal network.
- **State:** Qdrant Cloud, Upstash Redis.

## How ingestion works

There is no scheduler. When the agent asks about a ticker with no indexed filings, `edgar_fetch_tool` resolves the CIK, downloads the latest 10-K from SEC EDGAR, chunks it by section, embeds it and upserts it to Qdrant (idempotently), so the first report on a new ticker is slower than later ones.

## Known limitations & roadmap

- **Evaluation harness not built yet.** The plan is a DeepEval suite (faithfulness, recall@5, groundedness, tool-selection accuracy) over a 25-question golden set, gating deploys in CI. No quality numbers are claimed until it exists.
- **Free-tier data limits.** Alpha Vantage allows 25 requests/day; heavy use will degrade reports to `partial`. Swapping providers or extending the cache is the fix.
- **History is per-browser.** The backend has no list-all/delete endpoint, so the report index lives in `localStorage`.
- **Report quality is prompt-bound.** Source selection from web search can be weak, and the model can misstate figures it reads from filings; citations let a reader verify, but the output is not investment advice.
- **No live quotes in the UI** until a report finishes.
