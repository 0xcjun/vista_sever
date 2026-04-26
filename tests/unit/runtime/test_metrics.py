from __future__ import annotations

import json
from io import StringIO

import pytest

from vista_fc.runtime.logging import configure_logging, log_context
from vista_fc.runtime.metrics import (
    HANDLER_DURATION_MS,
    HANDLER_ERROR_TOTAL,
    HANDLER_STATUS_TOTAL,
    emit_metric,
)


def _lines(sink: StringIO) -> list[dict]:
    return [json.loads(ln) for ln in sink.getvalue().splitlines() if ln.strip()]


def test_emit_metric_writes_structured_line(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = StringIO()
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging(sink=sink)

    emit_metric(name=HANDLER_DURATION_MS, value=123.4, unit="ms")

    records = _lines(sink)
    assert len(records) == 1
    r = records[0]
    assert r["event"] == "metric"
    assert r["metric_name"] == HANDLER_DURATION_MS
    assert r["metric_value"] == 123.4
    assert r["metric_unit"] == "ms"


def test_emit_metric_includes_context_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = StringIO()
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging(sink=sink)

    with log_context(run_id="r1", user_hash="u1", workspace_id="EXP_1", function_name="factor-detect"):
        emit_metric(
            name=HANDLER_STATUS_TOTAL,
            value=1,
            status="succeeded",
        )
    r = _lines(sink)[0]
    assert r["metric_name"] == HANDLER_STATUS_TOTAL
    assert r["metric_status"] == "succeeded"
    assert r["run_id"] == "r1"
    assert r["function_name"] == "factor-detect"


def test_emit_metric_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = StringIO()
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging(sink=sink)

    emit_metric(
        name=HANDLER_ERROR_TOTAL,
        value=1,
        status="failed",
        error_code="OSS_ETAG_CONFLICT",
    )
    r = _lines(sink)[0]
    assert r["metric_error_code"] == "OSS_ETAG_CONFLICT"
    assert r["metric_status"] == "failed"
