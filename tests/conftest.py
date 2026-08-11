from __future__ import annotations

from pathlib import Path

import pytest

from app import logging_config


@pytest.fixture(autouse=True)
def isolate_log_file(monkeypatch, tmp_path: Path):
    """Test khong duoc ghi vao data/logs.jsonl that.

    File do la nguon chuan cua dashboard va cua validate_logs.py; neu test ghi
    lan vao thi evidence se lan traffic khong co that.
    """
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    return tmp_path / "logs.jsonl"
