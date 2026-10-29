"""Unit test for the app wiring: routers are mounted and /health responds."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def preflight(origin: str):
    return client.options(
        "/analyze",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )


def test_cors_allows_local_dev_origin():
    assert preflight("http://localhost:5173").headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_allows_vercel_preview_origin():
    origin = "https://stock-research-git-main-someone.vercel.app"
    assert preflight(origin).headers.get("access-control-allow-origin") == origin


def test_cors_rejects_unknown_origin():
    assert "access-control-allow-origin" not in preflight("https://evil.example.com").headers
    assert "access-control-allow-origin" not in preflight("https://vercel.app.evil.com").headers
