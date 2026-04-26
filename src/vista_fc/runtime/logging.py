"""Structured logging with per-invocation context binding.

`configure_logging` installs a JSON sink on loguru (env `LOG_FORMAT=json`);
`log_context(...)` is a context manager that binds run_id / user_hash /
workspace_id / function_name so every log line within the block carries them.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
from collections.abc import Callable, Iterator
from typing import IO, TYPE_CHECKING, Any, TextIO, cast

from loguru import logger

if TYPE_CHECKING:
    from loguru import Message as LoguruMessage

_REDACTED = "***REDACTED***"

# Patterns that must never appear in logs regardless of how they reached the record.
# Kept intentionally conservative: match high-entropy tokens we know the platform
# uses, not arbitrary long strings (which would eat legitimate payloads).
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),  # Anthropic / OpenAI-style
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),  # OAuth Authorization header
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}"),  # JWT
    re.compile(r"LTAI[A-Za-z0-9]{8,}"),  # Aliyun AccessKeyId
)

# Extra-field keys whose values are always redacted (case-insensitive substring match).
_SECRET_KEY_HINTS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "accesskey",
    "private_key",
    "authorization",
    "session_key",
)


def _redact_text(text: str) -> str:
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub(_REDACTED, out)
    return out


def _is_secret_key(key: str) -> bool:
    low = key.lower()
    return any(hint in low for hint in _SECRET_KEY_HINTS)


def _redact_value(key: str, value: Any) -> Any:
    if _is_secret_key(key):
        return _REDACTED
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, v) for v in value]
    return value


def _build_json_sink(target: IO[str]) -> Callable[[LoguruMessage], None]:
    """Return a sink callable that serializes each record to JSON and writes to target.

    We use a sink callable rather than a format string so loguru never tries to
    ``.format_map()`` our JSON output (which would fail on the ``{...}`` we emit).
    """

    def _sink(message: LoguruMessage) -> None:
        record: dict[str, Any] = dict(message.record)
        payload: dict[str, Any] = {
            "ts": record["time"].isoformat(),
            "level": record["level"].name,
            "message": _redact_text(record["message"]),
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
        }
        extra: dict[str, Any] = record["extra"]
        # Whitelist: only safe context keys are serialized. Any secret-named extra
        # attached via logger.bind() is dropped entirely.
        safe_keys = (
            "run_id",
            "user_hash",
            "workspace_id",
            "function_name",
            "phase",
            "request_id",
            # Metric emission fields (see runtime/metrics.py); fixed-schema, not PII.
            "event",
            "metric_name",
            "metric_value",
            "metric_unit",
            "metric_status",
            "metric_error_code",
        )
        for key in safe_keys:
            if key in extra and not _is_secret_key(key):
                payload[key] = _redact_value(key, extra[key])
        target.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return _sink


def configure_logging(*, sink: IO[str] | None = None) -> None:
    """Install the global loguru sink. Idempotent — removes prior sinks first."""
    logger.remove()
    target: IO[str] = sink if sink is not None else sys.stdout
    fmt = os.environ.get("LOG_FORMAT", "json").lower()
    if fmt == "json":
        logger.add(_build_json_sink(target), level="INFO")
    else:
        # loguru's add() sink overload accepts TextIO; IO[str] is structurally compatible.
        logger.add(
            cast(TextIO, target),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="INFO",
        )


@contextlib.contextmanager
def log_context(
    *,
    run_id: str | None = None,
    user_hash: str | None = None,
    workspace_id: str | None = None,
    function_name: str | None = None,
    phase: str | None = None,
    request_id: str | None = None,
) -> Iterator[None]:
    bindings: dict[str, str] = {}
    for key, val in [
        ("run_id", run_id),
        ("user_hash", user_hash),
        ("workspace_id", workspace_id),
        ("function_name", function_name),
        ("phase", phase),
        ("request_id", request_id),
    ]:
        if val is not None:
            bindings[key] = val
    with logger.contextualize(**bindings):
        yield
