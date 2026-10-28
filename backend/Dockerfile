# ── Single-stage production image ─────────────────────────────────────────────
# Runs identically in docker compose (local dev) and on Railway (production).
# Railway's MCP-server service uses the same image but overrides the start command:
#   fastmcp run app/mcp_servers/server.py --transport http --port $PORT
FROM python:3.11-slim-bookworm

# PYTHONPATH: the fastmcp CLI doesn't add the cwd to sys.path, so `import app` fails without it.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Apply OS-level CVE patches released after the base image was published,
# and install curl (used by the compose health checks).
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir \
 && pip install --no-cache-dir -r requirements.txt


COPY app/ ./app/

# ── Least-privilege runtime user ───────────────────────────────────────────────
# Needs a real, writable HOME: the Agent SDK's bundled Claude CLI writes config/cache there.
RUN useradd --create-home --home-dir /home/appuser --shell /bin/false appuser
ENV HOME=/home/appuser
USER appuser

# Backend FastAPI app listens on 8000; Railway injects $PORT and overrides this.
EXPOSE 8000

# Default: FastAPI backend via uvicorn.
# Override for the MCP-server Railway service:
#   fastmcp run app/mcp_servers/server.py --transport http --port $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
