from __future__ import annotations

import json
import socket
import sys
import threading
import time
import types
import urllib.error
import urllib.request
from typing import Any

import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_health(port: int, *, timeout_s: float = 3.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.05)
    raise RuntimeError(f"server on :{port} did not become healthy within {timeout_s}s")


def _start_server(spec: str, port: int) -> threading.Thread:
    from vista_fc.runtime.adapter.__main__ import serve

    th = threading.Thread(target=serve, args=(spec, port), daemon=True)
    th.start()
    _wait_health(port)
    return th


def _echo_handler(event: dict[str, Any], context: object) -> dict[str, Any]:  # noqa: ARG001
    return {"status": "succeeded", "echo": event}


def _context_handler(event: dict[str, Any], context: object) -> dict[str, Any]:  # noqa: ARG001
    return {
        "status": "succeeded",
        "request_id": getattr(context, "request_id", ""),
        "access_key_id": getattr(context, "access_key_id", ""),
        "access_key_secret": getattr(context, "access_key_secret", ""),
        "security_token": getattr(context, "security_token", ""),
    }


def _bad_handler(event: dict[str, Any], context: object) -> dict[str, Any]:  # noqa: ARG001
    raise RuntimeError("boom")


def test_invoke_routes_to_handler() -> None:
    mod = types.ModuleType("_fake_echo_http_adapter_test")
    mod.handler = _echo_handler  # type: ignore[attr-defined]
    sys.modules["_fake_echo_http_adapter_test"] = mod

    port = _free_port()
    _start_server("_fake_echo_http_adapter_test:handler", port)

    payload = {"tenant": {"user_hash": "u"}}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/invoke",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        body = json.loads(resp.read())
    assert body["status"] == "succeeded"
    assert body["echo"] == payload


def test_invoke_passes_fc_credentials_headers_to_context() -> None:
    mod = types.ModuleType("_fake_context_http_adapter_test")
    mod.handler = _context_handler  # type: ignore[attr-defined]
    sys.modules["_fake_context_http_adapter_test"] = mod

    port = _free_port()
    _start_server("_fake_context_http_adapter_test:handler", port)

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/invoke",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "x-fc-request-id": "req-1",
            "x-fc-access-key-id": "fc-ak",
            "x-fc-access-key-secret": "fc-sk",  # pragma: allowlist secret
            "x-fc-security-token": "fc-token",
        },
    )
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        body = json.loads(resp.read())
    assert body == {
        "status": "succeeded",
        "request_id": "req-1",
        "access_key_id": "fc-ak",
        "access_key_secret": "fc-sk",  # pragma: allowlist secret
        "security_token": "fc-token",
    }


def test_invoke_handler_exception_returns_500() -> None:
    mod = types.ModuleType("_fake_bad_http_adapter_test")
    mod.handler = _bad_handler  # type: ignore[attr-defined]
    sys.modules["_fake_bad_http_adapter_test"] = mod

    port = _free_port()
    _start_server("_fake_bad_http_adapter_test:handler", port)

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/invoke",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(req, timeout=2.0)
    assert ei.value.code == 500
    body = json.loads(ei.value.read())
    assert body["errorType"] == "RuntimeError"
    assert "boom" in body["errorMessage"]


def test_bad_json_returns_400() -> None:
    mod = types.ModuleType("_fake_for_400_http_adapter_test")
    mod.handler = _echo_handler  # type: ignore[attr-defined]
    sys.modules["_fake_for_400_http_adapter_test"] = mod

    port = _free_port()
    _start_server("_fake_for_400_http_adapter_test:handler", port)

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/invoke",
        data=b"not json at all",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(req, timeout=2.0)
    assert ei.value.code == 400
