from __future__ import annotations

import json
from pathlib import Path

from app import logging_config


def _read(log_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_exception_traceback_is_scrubbed(monkeypatch, tmp_path: Path) -> None:
    """format_exc_info phai chay truoc scrub_event, neu khong PII lot qua traceback."""
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    logging_config.configure_logging()
    log = logging_config.get_logger()

    try:
        raise ValueError("contact student@vinuni.edu.vn or 0987654321")
    except ValueError:
        log.exception("request_failed", service="api")

    rendered = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in rendered
    assert "0987654321" not in rendered
    assert "REDACTED_EMAIL" in rendered
    assert "REDACTED_PHONE_VN" in rendered


def test_nested_payload_and_lists_are_scrubbed(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    logging_config.configure_logging()
    log = logging_config.get_logger()

    log.info(
        "request_received",
        service="api",
        payload={
            "docs": ["mail student@vinuni.edu.vn"],
            "nested": {"deep": {"phone": "0987654321"}},
        },
    )

    record = _read(log_path)[0]
    assert record["payload"]["docs"] == ["mail [REDACTED_EMAIL]"]
    assert record["payload"]["nested"]["deep"]["phone"] == "[REDACTED_PHONE_VN]"
