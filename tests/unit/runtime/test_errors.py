from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from vista_fc.runtime.errors import (
    ERROR_CODES,
    FcError,
    classify,
)


def test_error_codes_are_frozen() -> None:
    assert {
        "VISTA_COMPUTE_TIMEOUT",
        "VISTA_LLM_RATE_LIMIT",
        "VISTA_LOGIC_ERROR",
        "OSS_READ_FAIL",
        "OSS_WRITE_FAIL",
        "OSS_ETAG_CONFLICT",
        "CLICKHOUSE_CONNECT",
        "WORKSPACE_NOT_FOUND",
        "INPUT_VALIDATION",
    } <= set(ERROR_CODES)


def test_classify_value_error_is_logic_error() -> None:
    fc = classify(ValueError("bad input"))
    assert fc.code == "VISTA_LOGIC_ERROR"
    assert fc.retriable is False


def test_classify_pydantic_validation_error() -> None:
    class M(BaseModel):
        x: int

    with pytest.raises(ValidationError) as ei:
        M(x="not-an-int")  # type: ignore[arg-type]
    fc = classify(ei.value)
    assert fc.code == "INPUT_VALIDATION"
    assert fc.retriable is False


def test_classify_timeout() -> None:
    fc = classify(TimeoutError("slow"))
    assert fc.code == "VISTA_COMPUTE_TIMEOUT"
    assert fc.retriable is True


def test_classify_connection_error_is_retriable() -> None:
    fc = classify(ConnectionError("refused"))
    assert fc.code == "CLICKHOUSE_CONNECT"
    assert fc.retriable is True


def test_classify_generic_unknown_is_logic_error() -> None:
    fc = classify(RuntimeError("something weird"))
    assert fc.code == "VISTA_LOGIC_ERROR"
    assert fc.retriable is False


def test_fc_error_carries_trace_id() -> None:
    e = FcError(code="OSS_READ_FAIL", message="x", retriable=True, trace_id="t1")
    assert e.trace_id == "t1"
