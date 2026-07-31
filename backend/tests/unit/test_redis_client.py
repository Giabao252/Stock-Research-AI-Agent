"""
Unit tests for clients/redis.py. _client's methods are always mocked here — a
real round-trip against live Upstash is a separate manual verification step
(see the Phase 3 plan), consistent with never hitting real services in this
suite.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.clients.redis import (
    MAX_BUFFERED_MESSAGES,
    RedisSessionError,
    append_message,
    delete_session,
    get_session,
    save_session,
)
from app.models.session import SessionState


def make_session(**overrides) -> SessionState:
    base = dict(
        session_id="sess-1", ticker="AAPL", status="running", messages=[],
        partial_report=None, error_message=None, created_at=datetime(2026, 1, 1),
    )
    base.update(overrides)
    return SessionState(**base)


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------

async def test_get_session_returns_none_on_miss():
    with patch("app.clients.redis._client.get", new=AsyncMock(return_value=None)):
        result = await get_session("sess-1")
    assert result is None


async def test_get_session_parses_json_on_hit():
    session = make_session()
    with patch("app.clients.redis._client.get", new=AsyncMock(return_value=session.model_dump_json())):
        result = await get_session("sess-1")
    assert result == session


async def test_get_session_wraps_exception():
    with patch("app.clients.redis._client.get", new=AsyncMock(side_effect=RuntimeError("timeout"))):
        with pytest.raises(RedisSessionError):
            await get_session("sess-1")


# ---------------------------------------------------------------------------
# save_session
# ---------------------------------------------------------------------------

async def test_save_session_calls_set_with_ttl_and_json():
    session = make_session()
    with patch("app.clients.redis._client.set", new=AsyncMock()) as mock_set:
        await save_session(session)

    args, kwargs = mock_set.call_args
    assert args[0] == "session:sess-1"
    assert args[1] == session.model_dump_json()
    assert kwargs["ex"] == 3600


async def test_save_session_wraps_exception():
    with patch("app.clients.redis._client.set", new=AsyncMock(side_effect=RuntimeError("timeout"))):
        with pytest.raises(RedisSessionError):
            await save_session(make_session())


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

async def test_delete_session_calls_delete_with_key():
    with patch("app.clients.redis._client.delete", new=AsyncMock()) as mock_delete:
        await delete_session("sess-1")
    mock_delete.assert_awaited_once_with("session:sess-1")


async def test_delete_session_wraps_exception():
    with patch("app.clients.redis._client.delete", new=AsyncMock(side_effect=RuntimeError("timeout"))):
        with pytest.raises(RedisSessionError):
            await delete_session("sess-1")


# ---------------------------------------------------------------------------
# append_message
# ---------------------------------------------------------------------------

async def test_append_message_raises_when_session_missing():
    with patch("app.clients.redis._client.get", new=AsyncMock(return_value=None)):
        with pytest.raises(RedisSessionError):
            await append_message("sess-1", "user", "hello")


async def test_append_message_appends_and_saves():
    session = make_session(messages=[{"role": "user", "content": "first"}])
    with (
        patch("app.clients.redis._client.get", new=AsyncMock(return_value=session.model_dump_json())),
        patch("app.clients.redis._client.set", new=AsyncMock()) as mock_set,
    ):
        await append_message("sess-1", "assistant", "second")

    saved = SessionState.model_validate_json(mock_set.call_args[0][1])
    assert [m["content"] for m in saved.messages] == ["first", "second"]


async def test_append_message_truncates_to_last_8_turns():
    messages = [{"role": "user", "content": str(i)} for i in range(MAX_BUFFERED_MESSAGES)]
    session = make_session(messages=messages)
    with (
        patch("app.clients.redis._client.get", new=AsyncMock(return_value=session.model_dump_json())),
        patch("app.clients.redis._client.set", new=AsyncMock()) as mock_set,
    ):
        await append_message("sess-1", "user", "new message")

    saved = SessionState.model_validate_json(mock_set.call_args[0][1])
    assert len(saved.messages) == MAX_BUFFERED_MESSAGES
    assert saved.messages[-1]["content"] == "new message"
    assert saved.messages[0]["content"] == "1"  # oldest ("0") dropped
