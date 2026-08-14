"""
FastAPI application entry point.

Startup: initialises Qdrant collections (idempotent).
Routers:
    gateway  — POST /analyze, DELETE /sessions/{id}, GET /health
    agent    — GET /sessions/{id}/stream, POST /ask
    reports  — GET /reports, GET /reports/{id}, GET /chunks/{id}
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.clients import qdrant as qdrant_client
from app.routers.agent import router as agent_router
from app.routers.gateway import router as gateway_router
from app.routers.reports import router as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run once on startup: ensure Qdrant collections + payload indexes exist."""
    await qdrant_client.init_collections()
    yield


app = FastAPI(
    title="Stock Research Agent",
    description="Agentic RAG system for grounded, cited stock research reports.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",       # Vite dev server
        "http://localhost:4173",       # Vite preview
        "https://*.vercel.app",        # Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gateway_router)
app.include_router(agent_router)
app.include_router(reports_router)
