from __future__ import annotations

import contextlib
import json
from io import StringIO

import pytest

from vista_fc.runtime.logging import configure_logging, log_context


def test_json_line_has_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = StringIO()
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging(sink=sink)
    from loguru import logger

    with log_context(run_id="r1", user_hash="u1", workspace_id="EXP_1", function_name="factor-detect"):
        logger.info("hello")

    lines = [ln for ln in sink.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["message"] == "hello"
    assert rec["run_id"] == "r1"
    assert rec["user_hash"] == "u1"
    assert rec["workspace_id"] == "EXP_1"
    assert rec["function_name"] == "factor-detect"
    assert rec["level"] == "INFO"


def test_console_format_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = StringIO()
    monkeypatch.setenv("LOG_FORMAT", "console")
    configure_logging(sink=sink)
    from loguru import logger

    logger.info("plain line")
    out = sink.getvalue()
    assert "plain line" in out
    with contextlib.suppress(json.JSONDecodeError):
        for line in out.splitlines():
            if line.strip():
                json.loads(line)  # may raise; acceptable in console mode
