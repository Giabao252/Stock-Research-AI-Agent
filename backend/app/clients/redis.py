"""
Upstash Redis client: session state load/save/clear and the /ask conversation buffer.

Public API:
    get_session(session_id: str)                       -> SessionState | None
    save_session(session: SessionState)                -> None
    delete_session(session_id: str)                     -> None
    append_message(session_id, role, content)           -> None
"""

from upstash_redis.asyncio import Redis

from app.config import settings
from app.models.session import SessionState

SESSION_TTL_SECONDS = 3600  # safety-net expiry; DELETE /sessions/{id} clears it explicitly
MAX_BUFFERED_MESSAGES = 8

_client = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)


class RedisSessionError(Exception):
    """Raised when a session record can't be read or written."""


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def get_session(session_id: str) -> SessionState | None:
    """Return the session record, or None if it doesn't exist or has expired."""
    try:
        raw = await _client.get(_session_key(session_id))
    except Exception as exc:
        raise RedisSessionError(f"Failed to read session {session_id}: {exc}") from exc

    if raw is None:
        return None
    return SessionState.model_validate_json(raw)


async def save_session(session: SessionState) -> None:
    """Upsert the session record as a JSON blob, refreshing its TTL."""
    try:
        await _client.set(
            _session_key(session.session_id),
            session.model_dump_json(),
            ex=SESSION_TTL_SECONDS,
        )
    except Exception as exc:
        raise RedisSessionError(f"Failed to save session {session.session_id}: {exc}") from exc


async def delete_session(session_id: str) -> None:
    """Remove the session record. No-op if it's already gone."""
    try:
        await _client.delete(_session_key(session_id))
    except Exception as exc:
        raise RedisSessionError(f"Failed to delete session {session_id}: {exc}") from exc


async def append_message(session_id: str, role: str, content: str) -> None:
    """Append a turn to the session's conversation buffer, truncated to the last 8 turns.

    Raises RedisSessionError if the session doesn't exist — the caller
    (routers/agent.py's /ask handler) is expected to have already created it.
    """
    session = await get_session(session_id)
    if session is None:
        raise RedisSessionError(f"Cannot append message: session {session_id} not found")

    session.messages.append({"role": role, "content": content})
    session.messages = session.messages[-MAX_BUFFERED_MESSAGES:]
    await save_session(session)
