from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.middleware import CORRELATION_ID_PATTERN

PAYLOAD = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "Explain observability",
}


def test_generated_correlation_id_matches_contract() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json=PAYLOAD)

    correlation_id = response.headers["x-request-id"]
    assert CORRELATION_ID_PATTERN.fullmatch(correlation_id)
    assert response.json()["correlation_id"] == correlation_id


def test_valid_incoming_correlation_id_is_reused() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat", json=PAYLOAD, headers={"x-request-id": "req-0123abcd"}
        )

    assert response.headers["x-request-id"] == "req-0123abcd"


def test_malformed_incoming_correlation_id_is_replaced() -> None:
    """Khong tin header cua client: gia tri sai format se pha vo truy vet log."""
    with TestClient(app) as client:
        response = client.post("/chat", json=PAYLOAD, headers={"x-request-id": "MISSING"})

    correlation_id = response.headers["x-request-id"]
    assert correlation_id != "MISSING"
    assert CORRELATION_ID_PATTERN.fullmatch(correlation_id)


def test_response_time_header_is_present() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json=PAYLOAD)

    assert float(response.headers["x-response-time-ms"]) > 0


def test_wall_clock_duration_is_logged_and_covers_agent_latency(isolate_log_file: Path) -> None:
    """duration_ms (wall-clock) phai bao trum latency_ms (chi do ben trong agent).

    Khoang chenh giua hai so chinh la thoi gian request nam cho — thu bi mat
    hoan toan neu chi do latency trong agent.run.
    """
    with TestClient(app) as client:
        response = client.post("/chat", json=PAYLOAD)

    events = [
        json.loads(line)
        for line in isolate_log_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed = next(e for e in events if e["event"] == "request_completed")
    sent = next(e for e in events if e["event"] == "response_sent")

    assert completed["service"] == "http"
    assert completed["status_code"] == 200
    assert completed["correlation_id"] == response.headers["x-request-id"]
    assert completed["duration_ms"] >= sent["latency_ms"]
