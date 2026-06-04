"""Smoke tests for the FastAPI app that don't require a live LLM."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ask_rejects_empty_question():
    # Pydantic min_length=1 -> 422 before the agent ever runs.
    res = client.post("/ask", json={"question": ""})
    assert res.status_code == 422


def test_cors_headers_present_for_allowed_origin():
    res = client.options(
        "/ask",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
