from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from handlers._base import run_handler


class _In(BaseModel):
    hello: str


class _Out(BaseModel):
    echo: str


def _tenant_dict() -> dict:
    return {
        "user_hash": "u",
        "workspace_id": "EXP_1",
        "workspace_kind": "research",
        "run_id": "r",
        "requested_at": datetime.now(UTC).isoformat(),
    }


def _mk_event(payload: dict) -> dict:
    return {"tenant": _tenant_dict(), "payload": payload}


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_success_envelope(mock_oss_cls: MagicMock, mock_ws_cls: MagicMock) -> None:
    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        return _Out(echo=payload.hello)

    result = run_handler(
        event=_mk_event({"hello": "world"}),
        context=None,
        input_cls=_In,
        output_cls=_Out,
        service=service,
        function_name="test-fn",
    )
    assert result["status"] == "succeeded"
    assert result["payload"]["echo"] == "world"
    assert result["error"] is None


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_failure_maps_to_fc_error(mock_oss_cls: MagicMock, mock_ws_cls: MagicMock) -> None:
    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    def service(**_kwargs) -> _Out:
        raise RuntimeError("boom")

    result = run_handler(
        event=_mk_event({"hello": "x"}),
        context=None,
        input_cls=_In,
        output_cls=_Out,
        service=service,
        function_name="test-fn",
    )
    assert result["status"] == "failed"
    assert result["error"]["code"] == "VISTA_LOGIC_ERROR"
    assert result["error"]["retriable"] is False


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_input_validation_maps_to_input_validation_code(mock_oss_cls: MagicMock, mock_ws_cls: MagicMock) -> None:
    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    def service(**_kwargs) -> _Out:
        return _Out(echo="x")

    result = run_handler(
        event={"tenant": _tenant_dict(), "payload": {"wrong": "field"}},
        context=None,
        input_cls=_In,
        output_cls=_Out,
        service=service,
        function_name="test-fn",
    )
    assert result["status"] == "failed"
    assert result["error"]["code"] == "INPUT_VALIDATION"
