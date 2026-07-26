"""
Unit test for main.py's only route.

root() returns {"FastAPI project is running"} — a Python set literal, not a
dict, despite the curly-brace syntax looking like one. FastAPI's
jsonable_encoder happens to special-case set/frozenset by converting to a
list before serializing, so this doesn't crash — it just silently returns a
JSON array instead of an object. This test pins the actual current behavior;
it is not asserting that behavior is correct.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_root_body_is_actually_a_json_array_not_an_object():
    # Documents the set-vs-dict surprise in main.py's root() — flagged, not fixed,
    # since main.py isn't wired into anything yet (no routers included).
    response = client.get("/")
    assert response.json() == ["FastAPI project is running"]
