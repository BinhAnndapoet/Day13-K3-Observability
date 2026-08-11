from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import build_dashboard

CONFIG = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "config" / "dashboard.yaml").read_text(encoding="utf-8")
)


def _log(event: str, ts: str, **fields) -> dict:
    return {
        "ts": ts,
        "level": "info",
        "service": "api",
        "event": event,
        "correlation_id": "req-0123abcd",
        **fields,
    }


def _records() -> list[dict]:
    return [
        _log("request_received", "2026-08-11T10:00:01Z"),
        _log("response_sent", "2026-08-11T10:00:02Z", latency_ms=100, cost_usd=0.001,
             tokens_in=30, tokens_out=90, quality_score=0.9),
        _log("request_received", "2026-08-11T10:01:01Z"),
        _log("response_sent", "2026-08-11T10:01:03Z", latency_ms=4000, cost_usd=0.002,
             tokens_in=30, tokens_out=110, quality_score=0.7),
        _log("request_received", "2026-08-11T10:01:30Z"),
        _log("request_failed", "2026-08-11T10:01:31Z", level="error", error_type="RuntimeError"),
    ]


def test_metrics_match_hand_computed_values() -> None:
    metrics = build_dashboard.compute_metrics(_records(), 60)

    assert metrics["requests"] == 3
    assert metrics["failures"] == 1
    assert metrics["latency"]["p50"] == 100
    assert metrics["latency"]["p95"] == 4000
    assert metrics["errors"]["error_rate_pct"] == pytest.approx(100 / 3)
    assert metrics["errors"]["count_by_value"] == {"RuntimeError": 1}
    assert metrics["cost"]["total"] == 0.003
    assert metrics["tokens"] == {"tokens_in": 60, "tokens_out": 200}
    assert metrics["quality"]["mean"] == 0.8
    assert list(metrics["traffic"]["by_minute"]) == ["10:00", "10:01"]


def test_percentile_matches_app_metrics() -> None:
    """Dashboard va /metrics phai dung cung dinh nghia percentile."""
    from app.metrics import percentile as app_percentile

    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for p in (50, 95, 99):
        assert build_dashboard.percentile(values, p) == app_percentile(values, p)


def test_threshold_breach_is_detected_per_panel() -> None:
    metrics = build_dashboard.compute_metrics(_records(), 60)
    values = build_dashboard.panel_values(metrics)
    panels = {p["id"]: p for p in CONFIG["dashboard"]["panels"]}

    latency = panels["latency"]["threshold"]
    assert not build_dashboard.threshold_ok(
        values["latency"], latency["operator"], latency["value"]
    )
    errors = panels["errors"]["threshold"]
    assert not build_dashboard.threshold_ok(
        values["errors"], errors["operator"], errors["value"]
    )
    cost = panels["cost"]["threshold"]
    assert build_dashboard.threshold_ok(values["cost"], cost["operator"], cost["value"])


def test_html_contains_all_six_panels_and_time_range(tmp_path: Path) -> None:
    metrics = build_dashboard.compute_metrics(_records(), 60)
    page = build_dashboard.render_html(CONFIG, metrics, "test", tmp_path / "logs.jsonl")

    for panel in CONFIG["dashboard"]["panels"]:
        assert panel["title"] in page
        assert panel["unit"] in page
    assert "2026-08-11 10:00:01Z" in page
    assert "Vuot nguong" in page


def test_pii_never_reaches_the_dashboard(tmp_path: Path) -> None:
    """Dashboard chi doc log da scrub; khong duoc render lai bat ky payload tho nao."""
    records = _records()
    records[0]["payload"] = {"message_preview": "mail student@vinuni.edu.vn"}
    metrics = build_dashboard.compute_metrics(records, 60)
    page = build_dashboard.render_html(CONFIG, metrics, "test", tmp_path / "logs.jsonl")

    assert "student@vinuni.edu.vn" not in page


def test_reader_handles_empty_and_malformed_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        json.dumps(_log("request_received", "2026-08-11T10:00:01Z")) + "\n\nnot-json\n",
        encoding="utf-8",
    )
    assert len(build_dashboard.read_records(log_path)) == 1
