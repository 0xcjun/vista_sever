"""FC custom-container HTTP adapter.

Behaviour:
- GET  /health    → 200 {"status":"ok"}
- POST /invoke    → body = FC event JSON; dispatched to the configured
                    handler (argv[1] = '<module>:<func>'); 200 with handler
                    return JSON on success; 500 with FC error shape on failure.
- Bad JSON → 400.

Usage:
    python -m vista_fc.runtime.adapter handlers.factor_plan:handler [port]

Port default: env FC_SERVER_PORT or 9000.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from vista_fc.runtime.adapter.handlers_loader import HandlerFn, load_handler
from vista_fc.runtime.logging import configure_logging

_HANDLER_FN: HandlerFn | None = None


def _write_json(handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]) -> None:
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


class _InvokeHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002, ARG002
        # Silence stderr; loguru owns log output.
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            _write_json(self, 200, {"status": "ok"})
            return
        _write_json(self, 404, {"errorType": "NotFound", "errorMessage": self.path})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/invoke":
            _write_json(self, 404, {"errorType": "NotFound", "errorMessage": self.path})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            event = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            _write_json(self, 400, {"errorType": "JSONDecodeError", "errorMessage": str(e)})
            return

        context = _FcContext(
            request_id=self.headers.get("x-fc-request-id", ""),
            function_name=self.headers.get("x-fc-function-name", ""),
            access_key_id=self.headers.get("x-fc-access-key-id", ""),
            access_key_secret=self.headers.get("x-fc-access-key-secret", ""),
            security_token=self.headers.get("x-fc-security-token", ""),
        )

        try:
            assert _HANDLER_FN is not None
            result = _HANDLER_FN(event, context)
            _write_json(self, 200, result)
        except Exception as e:  # noqa: BLE001
            _write_json(
                self,
                500,
                {
                    "errorType": type(e).__name__,
                    "errorMessage": str(e),
                    "stackTrace": traceback.format_exception(e),
                },
            )


class _FcContext:
    __slots__ = ("request_id", "function_name", "access_key_id", "access_key_secret", "security_token")

    def __init__(
        self,
        request_id: str,
        function_name: str,
        access_key_id: str,
        access_key_secret: str,
        security_token: str,
    ) -> None:
        self.request_id = request_id
        self.function_name = function_name
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.security_token = security_token


def serve(spec: str, port: int = 9000) -> None:
    global _HANDLER_FN
    _HANDLER_FN = load_handler(spec)
    configure_logging()

    server = ThreadingHTTPServer(("0.0.0.0", port), _InvokeHandler)
    server.serve_forever()


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "usage: python -m vista_fc.runtime.adapter <module>:<func> [port]",
            file=sys.stderr,
        )
        sys.exit(2)
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else int(os.environ.get("FC_SERVER_PORT", "9000"))
    serve(sys.argv[1], port)


if __name__ == "__main__":
    main()
