"""Suite-wide safety nets: no test may touch real Upstash Redis or wait on API throttles."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients import alpha_vantage
from app.clients import redis as redis_module


@pytest.fixture(autouse=True)
def isolate_redis(monkeypatch):
    # Tests that exercise the redis client patch individual methods on this stand-in.
    fake = MagicMock()
    fake.get = AsyncMock(return_value=None)
    fake.set = AsyncMock(return_value=True)
    fake.delete = AsyncMock(return_value=1)
    monkeypatch.setattr(redis_module, "_client", fake)


@pytest.fixture(autouse=True)
def no_alpha_vantage_throttle(monkeypatch):
    monkeypatch.setattr(alpha_vantage, "MIN_REQUEST_INTERVAL", 0.0)
