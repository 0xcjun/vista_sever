from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
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


class _Context:
    access_key_id = "fc-ak"
    access_key_secret = "fc-sk"  # pragma: allowlist secret
    security_token = "fc-token"


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
def test_build_workspace_passes_fc_context_credentials(mock_oss_cls: MagicMock, mock_ws_cls: MagicMock) -> None:
    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        return _Out(echo=payload.hello)

    run_handler(
        event=_mk_event({"hello": "world"}),
        context=_Context(),
        input_cls=_In,
        output_cls=_Out,
        service=service,
        function_name="test-fn",
    )

    mock_oss_cls.from_env.assert_called_once_with(
        access_key_id="fc-ak",
        access_key_secret="fc-sk",  # pragma: allowlist secret
        security_token="fc-token",
    )


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


@pytest.fixture
def in_memory_oss():
    """Mock OssClient where put/get/head form a consistent in-memory store.

    Used by the idempotency tests below to simulate a durable tombstone backend
    without touching real OSS.
    """
    store: dict[str, bytes] = {}
    mock = MagicMock()
    mock.bucket_name = "vista-fc-test"

    def _put(*, key, local_path, if_match_etag=None, if_none_match=None):  # noqa: ARG001
        if if_none_match == "*" and key in store:
            import oss2.exceptions as oss_exc

            raise oss_exc.PreconditionFailed(412, {}, b"", {})
        store[key] = local_path.read_bytes()
        from vista_fc.storage.oss_client import PutResult

        return PutResult(etag=f'"{hash(store[key])}"')

    def _get(*, key, local_path):
        if key not in store:
            import oss2.exceptions as oss_exc

            raise oss_exc.NoSuchKey(404, {}, b"", {})
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(store[key])

    def _exists(*, key):
        return key in store

    mock.put_from_file.side_effect = _put
    mock.get_to_file.side_effect = _get
    mock.exists.side_effect = _exists
    return mock


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_idempotent_replay_returns_cached_result(
    mock_oss_cls: MagicMock,
    mock_ws_cls: MagicMock,
    in_memory_oss: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two invocations with the same (function_name, user_hash, run_id) must
    produce one service call and identical output (tombstone replay)."""
    monkeypatch.setenv("VISTA_FC_IDEMPOTENCY", "1")
    mock_oss_cls.from_env.return_value = in_memory_oss
    mock_ws_cls.return_value = MagicMock(oss=in_memory_oss)

    calls = {"n": 0}

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        calls["n"] += 1
        return _Out(echo=f"{payload.hello}-{calls['n']}")

    event = _mk_event({"hello": "world"})
    first = run_handler(
        event=event, context=None, input_cls=_In, output_cls=_Out, service=service, function_name="test-fn"
    )
    second = run_handler(
        event=event, context=None, input_cls=_In, output_cls=_Out, service=service, function_name="test-fn"
    )

    assert calls["n"] == 1, "service must run only once under idempotency replay"
    assert first == second, "replayed envelope must be byte-identical to the first"


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_idempotency_disabled_by_default(
    mock_oss_cls: MagicMock,
    mock_ws_cls: MagicMock,
    in_memory_oss: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without VISTA_FC_IDEMPOTENCY=1 the feature stays off (opt-in for safety)."""
    monkeypatch.delenv("VISTA_FC_IDEMPOTENCY", raising=False)
    mock_oss_cls.from_env.return_value = in_memory_oss
    mock_ws_cls.return_value = MagicMock(oss=in_memory_oss)

    calls = {"n": 0}

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        calls["n"] += 1
        return _Out(echo=f"{payload.hello}-{calls['n']}")

    event = _mk_event({"hello": "world"})
    run_handler(event=event, context=None, input_cls=_In, output_cls=_Out, service=service, function_name="test-fn")
    run_handler(event=event, context=None, input_cls=_In, output_cls=_Out, service=service, function_name="test-fn")
    assert calls["n"] == 2, "opt-in: feature off by default"


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_idempotency_skips_tombstone_on_failure(
    mock_oss_cls: MagicMock,
    mock_ws_cls: MagicMock,
    in_memory_oss: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed service must not write a tombstone so retries can succeed."""
    monkeypatch.setenv("VISTA_FC_IDEMPOTENCY", "1")
    mock_oss_cls.from_env.return_value = in_memory_oss
    mock_ws_cls.return_value = MagicMock(oss=in_memory_oss)

    calls = {"n": 0}

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return _Out(echo="ok")

    event = _mk_event({"hello": "world"})
    first = run_handler(
        event=event, context=None, input_cls=_In, output_cls=_Out, service=service, function_name="test-fn"
    )
    second = run_handler(
        event=event, context=None, input_cls=_In, output_cls=_Out, service=service, function_name="test-fn"
    )

    assert first["status"] == "failed"
    assert second["status"] == "succeeded"
    assert calls["n"] == 2


def _metric_records(capsys: pytest.CaptureFixture[str]) -> list[dict]:
    import json as _json

    out = capsys.readouterr().out
    records = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        try:
            rec = _json.loads(ln)
        except _json.JSONDecodeError:
            continue
        if rec.get("event") == "metric":
            records.append(rec)
    return records


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_success_emits_duration_and_status_metrics(
    mock_oss_cls: MagicMock,
    mock_ws_cls: MagicMock,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VISTA_FC_IDEMPOTENCY", raising=False)
    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    # Force reconfigure of the sink to stdout so capsys sees it.
    import handlers._base as base_mod

    base_mod._LOG_CONFIGURED = False

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        return _Out(echo=payload.hello)

    run_handler(
        event=_mk_event({"hello": "world"}),
        context=None,
        input_cls=_In,
        output_cls=_Out,
        service=service,
        function_name="test-fn",
    )
    metrics = _metric_records(capsys)
    names = {m["metric_name"] for m in metrics}
    assert "handler.duration_ms" in names
    assert "handler.status_total" in names
    # status tag carried on both
    by_name = {m["metric_name"]: m for m in metrics}
    assert by_name["handler.status_total"]["metric_status"] == "succeeded"
    assert by_name["handler.duration_ms"]["metric_value"] >= 0


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_failure_emits_error_metric_with_code(
    mock_oss_cls: MagicMock,
    mock_ws_cls: MagicMock,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VISTA_FC_IDEMPOTENCY", raising=False)
    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    import handlers._base as base_mod

    base_mod._LOG_CONFIGURED = False

    def service(**_kwargs) -> _Out:
        raise RuntimeError("boom")

    run_handler(
        event=_mk_event({"hello": "x"}),
        context=None,
        input_cls=_In,
        output_cls=_Out,
        service=service,
        function_name="test-fn",
    )
    metrics = _metric_records(capsys)
    err = [m for m in metrics if m["metric_name"] == "handler.error_total"]
    assert len(err) == 1
    assert err[0]["metric_error_code"] == "VISTA_LOGIC_ERROR"
    assert err[0]["metric_status"] == "failed"
