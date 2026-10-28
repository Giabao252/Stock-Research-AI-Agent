# ── Single-stage production image ─────────────────────────────────────────────
# Runs identically in docker compose (local dev) and on Railway (production).
# Railway's MCP-server service uses the same image but overrides the start command:
#   fastmcp run app/mcp_servers/server.py --transport http --port $PORT
FROM python:3.11.1-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Apply OS-level CVE patches released after the base image was published,
# and install curl (used by Docker's own health check probe).
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir \
 && pip install --no-cache-dir -r requirements.txt


COPY app/ ./app/

# ── Least-privilege runtime user ───────────────────────────────────────────────
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

# Backend FastAPI app listens on 8000; Railway injects $PORT and overrides this.
EXPOSE 8000

# Default: FastAPI backend via uvicorn.
# Override for the MCP-server Railway service:
#   fastmcp run app/mcp_servers/server.py --transport http --port $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
