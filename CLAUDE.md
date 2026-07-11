# Stock Research Agent — Claude Code Context

## What this project is
Production-grade agentic RAG system for stock research. An AI agent autonomously retrieves SEC filings, live financial data, and news to generate grounded, cited research reports with a visible reasoning chain streamed live to the browser.

This is a portfolio project targeting new grad AI engineering roles in 2027.

---

## Architecture overview

```
Frontend (Vercel)
  React + TypeScript + Tailwind CSS + Vite + Zod
  └── EventSource /sessions/{id}/stream  (SSE — live reasoning chain)
  └── POST /analyze, POST /ask, GET /reports/*

Backend (Railway — single consolidated service)
  FastAPI + Python + Pydantic
  ├── Gateway router  — auth, rate limiting, session creation
  └── Agent router    — runs the Agent SDK loop, exposes SSE stream

MCP servers (Railway — second consolidated service)
  FastAPI + MCP SDK (FastMCP)
  ├── rag_retrieval_tool  — BM25 + Qdrant dense + RRF + Cohere reranker
  ├── stock_data_tool     — Alpha Vantage: price, P/E, revenue, ratios
  ├── web_search_tool     — Tavily: recent news, analyst ratings
  ├── edgar_fetch_tool    — on-demand 10-K ingestion for unknown tickers
  └── code_execution_tool — RestrictedPython: P/E, PEG, YoY growth calcs

Managed external services
  Qdrant Cloud     — vector DB (filings collection + reports collection)
  Upstash Redis    — session state, conversation buffer
  Cloudflare R2    — raw EDGAR PDF storage, idempotency state
```

---

## Agent SDK — the core decision

This project uses **`claude-agent-sdk`** (not the raw `anthropic` Client SDK).

```bash
pip install claude-agent-sdk   # Python 3.10+ required
```

- Package: `claude-agent-sdk` on PyPI (renamed from `claude-code-sdk` in late 2025)
- Options class: `ClaudeAgentOptions` (not `ClaudeCodeOptions` — that is dead)
- Entry point: `query()` async generator — streams every message in the agent loop
- Docs: https://code.claude.com/docs/en/agent-sdk/overview

The SDK handles the tool loop, context compaction, and MCP integration.
You still own: session persistence (Redis), SSE translation (hooks → FastAPI), stop conditions, RAG pipeline, and all MCP server implementations.

**Dev model:** Groq free tier (Llama 3.1 70B) — swap to Claude for final demo.
Agent SDK reads `ANTHROPIC_BASE_URL` — point it at Groq-compatible endpoint during dev.

**Auth:** API key only. Never use claude.ai login for products built on the Agent SDK.

**Cost ceiling per run:** set `max_budget_usd=0.50` on `ClaudeAgentOptions`.

---

## Key conventions

### Backend (Python)
- All layers communicate via Pydantic models — never raw dicts between functions
- Every tool registered via `@tool` decorator on MCP server, not inline in agent config
- Agent SDK hooks used for SSE emission and self-reflection:
  - `PostToolUseHook` → emit `observe` SSE event + check if any claim lacks a source
  - `PreToolUseHook` → validate tool args, block any destructive calls
- Tool errors returned as typed error responses, never raised as exceptions to the agent
- `code_execution_tool` uses RestrictedPython — never raw `exec()`
- All secrets via environment variables — no hardcoded keys anywhere
- All env vars loaded from `app/config.py` (pydantic-settings) — never `os.getenv()` inline

### Frontend (TypeScript)
- Tailwind CSS only — no CSS files, no inline styles, no component libraries
- All API responses validated with Zod at runtime before use in components
- SSE events typed as a discriminated union — exhaustively switched on `type` field
- No business logic inside React components — all async logic lives in custom hooks
- Three-layer separation: `src/api/` (fetch + Zod), `src/hooks/` (state), `src/components/` (render)

### SSE event schema (enforced on both sides)
```typescript
type StreamEvent =
  | { type: 'thought';   content: string }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { type: 'observe';   summary: string }
  | { type: 'done';      report_id: string }
  | { type: 'error';     message: string }
```

### Output schema (enforced by Pydantic + Agent SDK structured outputs)
```python
class Claim(BaseModel):
    text: str
    chunk_id: str
    source_url: str
    doc_name: str

class ResearchReport(BaseModel):
    ticker: str
    bull_case: list[Claim]
    bear_case: list[Claim]
    verdict: Literal['bullish', 'bearish', 'neutral']
    confidence: float          # 0.0–1.0
    tool_trace: list[ToolCall] # every tool called + args + result summary
    metrics: dict              # P/E, revenue, market cap from stock_data_tool
    partial: bool
    partial_reason: str | None
    generated_at: datetime
```

---

## File map

```
stock-research-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, mounts all routers
│   │   ├── config.py                  # pydantic-settings: all env vars in one place
│   │   │
│   │   ├── routers/
│   │   │   ├── gateway.py             # POST /analyze, DELETE /sessions/{id}, GET /health
│   │   │   ├── agent.py               # GET /sessions/{id}/stream (SSE), POST /ask
│   │   │   └── reports.py             # GET /reports, GET /reports/{id}, GET /chunks/{id}
│   │   │
│   │   ├── agent/
│   │   │   ├── runner.py              # Agent SDK query() wrapper + hook wiring
│   │   │   ├── hooks.py               # PreToolUseHook, PostToolUseHook definitions
│   │   │   └── prompts.py             # system prompt templates
│   │   │
│   │   ├── rag/
│   │   │   ├── ingest.py              # orchestrator: calls edgar→chunker→embedder→qdrant
│   │   │   ├── retrieval.py           # BM25 + Qdrant dense + asyncio.gather + RRF + Cohere
│   │   │   ├── chunker.py             # section detection regex + section-aware chunking
│   │   │   └── embedder.py            # text-embedding-3-small, batches of 100
│   │   │
│   │   ├── clients/                   # one file per external service — HTTP logic only
│   │   │   ├── edgar.py               # ticker→CIK, CIK→filings list, fetch raw doc
│   │   │   ├── qdrant.py              # collection init, upsert, query helpers
│   │   │   ├── redis.py               # session load/save/clear
│   │   │   ├── cohere.py              # reranker call
│   │   │   ├── alpha_vantage.py       # price, P/E, revenue, ratios
│   │   │   └── tavily.py              # news search
│   │   │
│   │   ├── models/                    # Pydantic models split by domain
│   │   │   ├── report.py              # ResearchReport, Claim, ToolCall
│   │   │   ├── chunk.py               # Chunk, filings payload schema
│   │   │   ├── session.py             # SessionState
│   │   │   └── api.py                 # request/response schemas (AnalyzeRequest, Answer)
│   │   │
│   │   └── mcp_servers/
│   │       ├── server.py              # FastMCP app, mounts all tools
│   │       ├── rag_tool.py            # rag_retrieval_tool — imports clients/qdrant + rag/retrieval
│   │       ├── stock_tool.py          # stock_data_tool — imports clients/alpha_vantage
│   │       ├── search_tool.py         # web_search_tool — imports clients/tavily
│   │       ├── edgar_tool.py          # edgar_fetch_tool — imports clients/edgar + rag/ingest
│   │       └── code_tool.py           # code_execution_tool — RestrictedPython
│   │
│   ├── tests/
│   │   ├── eval/
│   │   │   ├── golden_dataset.json    # 25 Q&A pairs — DO NOT edit manually
│   │   │   └── test_eval.py           # DeepEval faithfulness + recall@5 + groundedness
│   │   └── unit/
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── railway.toml
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts              # typed fetch wrappers
│   │   │   └── schemas.ts             # Zod schemas mirroring all Pydantic models
│   │   ├── hooks/
│   │   │   ├── useAgentStream.ts      # EventSource → StreamEvent[] state
│   │   │   ├── useReport.ts           # fetch + cache a ResearchReport
│   │   │   └── useSession.ts          # session management
│   │   ├── components/
│   │   │   ├── ReasoningChain.tsx     # live Thought/tool_call/observe stream
│   │   │   ├── ReportDisplay.tsx      # bull/bear/verdict/confidence
│   │   │   ├── CitationDrawer.tsx     # slide-over showing raw chunk text
│   │   │   ├── MetricsHeader.tsx      # P/E, revenue, market cap row
│   │   │   └── PromptField.tsx        # follow-up question input
│   │   └── pages/
│   │       ├── Home.tsx               # search bar + intent detection
│   │       ├── Report.tsx             # full report view + follow-up chat
│   │       ├── History.tsx            # past reports list + compare
│   │       └── Compare.tsx            # multi-ticker side-by-side
│   │
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
├── .github/
│   └── workflows/
│       └── ci.yml                     # push → DeepEval → Docker build → ghcr.io → Railway
│
├── docker-compose.yml                 # local: backend + qdrant + redis (NOT frontend)
├── CLAUDE.md                          # this file
└── README.md
```

---

## Import rules (enforced)

```
routers/       → models/api.py, agent/runner.py, clients/redis.py
agent/         → models/report.py, models/session.py, clients/redis.py
rag/ingest.py  → clients/edgar.py, rag/chunker.py, rag/embedder.py, clients/qdrant.py
rag/retrieval  → clients/qdrant.py, clients/cohere.py, models/chunk.py
mcp_servers/   → clients/*, rag/ingest.py, rag/retrieval.py, models/*
clients/       → config.py only — no internal app imports
models/        → no internal app imports
config.py      → no internal app imports
```

No circular imports. `clients/` and `models/` are leaf nodes — they import nothing from the app.

---

## RAG pipeline — how it works

### Ingestion (offline, runs once per company)
```
EDGAR API → raw 10-K HTML/PDF
  → clients/edgar.py         — fetch raw doc bytes
  → rag/chunker.py           — section detection + section-aware chunking (512 tok, 50 overlap)
  → rag/embedder.py          — text-embedding-3-small, batches of 100
  → clients/qdrant.py        — idempotency check + upsert to filings collection
  → clients/r2.py            — raw PDF stored at {ticker}/{year}/10K.pdf
```

### Retrieval (live, per agent tool call, target <300ms)
```
query string
  → asyncio.gather(BM25 search, Qdrant dense search)  ← run in parallel
  → reciprocal rank fusion: score = Σ 1/(60 + rank)
  → Cohere reranker: top 20 → top 5
  → metadata filter: ticker + section applied at Qdrant query level
  → returns list[Chunk(text, chunk_id, ticker, section, year, source_url, score)]
```

### Two Qdrant collections
- `filings` — one point per chunk, 1536d vector, payload per chunk above
- `reports` — one point per completed ResearchReport, enables long-term memory + comparison

---

## Data flow — session lifecycle

```
POST /analyze {ticker, session_id}
  → create session in Redis: {messages:[], status:"running", partial_report:{}}
  → load prior reports for this ticker from Qdrant reports collection
  → start Agent SDK query() as FastAPI background task
  → return 202 + session_id immediately

GET /sessions/{id}/stream (SSE — held open)
  → Agent SDK hooks translate to StreamEvent discriminated union
  → each event yielded via FastAPI StreamingResponse
  → on done: store ResearchReport in Qdrant, clear Redis session, emit done event

POST /ask {question, ticker, session_id}
  → load conversation buffer from Redis (last 8 turns)
  → run Agent SDK query() with question-scoped system prompt
  → return Answer(text, sources[])
```

---

## Deployment

### Local development
```bash
docker compose up          # starts backend service + qdrant + redis
cd frontend && npm run dev # Vite dev server on :5173 (outside Docker for HMR)
```
`.env.local` holds: `VITE_API_BASE_URL`, `ANTHROPIC_API_KEY` (or Groq key during dev),
`QDRANT_URL`, `QDRANT_API_KEY`, `UPSTASH_REDIS_URL`, `TAVILY_API_KEY`, `ALPHA_VANTAGE_KEY`,
`COHERE_API_KEY`, `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`

### Production
- **Frontend:** Vercel — auto-deploys from GitHub on push to `main`
- **Backend:** Railway service 1 — gateway + agent + reports routers in one FastAPI app
- **MCP servers:** Railway service 2 — all 5 MCP servers in one FastMCP app
- **Qdrant:** Qdrant Cloud free tier (1GB)
- **Redis:** Upstash free tier (10k commands/day)
- **Files:** Cloudflare R2 (10GB free)
- **CI/CD:** GitHub Actions — push → DeepEval suite → Docker build → ghcr.io → Railway redeploy

### Railway config (`railway.toml`)
```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "on-failure"

[env]
RAILWAY_DEPLOYMENT_TIMEOUT = "600"    # agent runs can take up to 3 minutes
```

---

## Eval harness

- Framework: DeepEval (pytest-native)
- Golden dataset: `backend/tests/eval/golden_dataset.json` — 25 Q&A pairs across NVDA, AAPL, MSFT, TSLA, AMZN
- **DO NOT edit golden_dataset.json manually** — use the dataset builder script
- Metrics: faithfulness, recall@5, groundedness rate (target >90%), tool selection accuracy
- Runs in GitHub Actions on every push to `main` — blocks deploy if any metric fails
- README badges show live scores

---

## What not to touch

- Never edit `tests/eval/golden_dataset.json` by hand
- Never add inline styles to React components — Tailwind only
- Never use raw `exec()` — code execution goes through RestrictedPython only
- Never store API keys in code — use Railway env vars and `.env.local`
- Never call `os.getenv()` inline — use `app/config.py` Settings class only
- Never use `claude-code-sdk` or `ClaudeCodeOptions` — both are dead/renamed
- Never put business logic inside React components — hooks only
- Never use `sudo` with npm
- Never import across layers in violation of the import rules above

---

## Interview talking points this project demonstrates

- Hybrid RAG: BM25 + dense retrieval in parallel, RRF fusion, Cohere reranking — with measured recall@5 before/after
- Section-aware chunking vs fixed chunking — empirically compared
- Agent SDK: tool loop, hooks for SSE emission, structured outputs, budget control
- MCP servers: custom tool registration, FastMCP pattern, permission scoping
- Context engineering: session persistence in Redis, on-demand ingestion, self-reflection via PostToolUseHook
- Eval harness: DeepEval in CI, faithfulness + groundedness metrics, golden dataset
- Cost-pragmatic deployment: Railway + Vercel + Qdrant Cloud + Upstash — $5/month total
- TypeScript end-to-end: Zod mirrors Pydantic, discriminated union SSE events, three-layer frontend architecture
- Clean module boundaries: clients/ and models/ as leaf nodes, explicit import rules enforced across all layers