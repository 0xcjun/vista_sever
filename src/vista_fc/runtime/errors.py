"""Error classification and structured error dataclass.

Spec §5.1 + §6.2: errors drive FnF retry policy. Map raw exceptions to
one of 9 stable codes; attach retriable flag so FnF can decide to retry.
"""

from __future__ import annotations

import socket
import uuid
from dataclasses import dataclass
from typing import Final

from pydantic import ValidationError

ERROR_CODES: Final[tuple[str, ...]] = (
    "VISTA_COMPUTE_TIMEOUT",
    "VISTA_LLM_RATE_LIMIT",
    "VISTA_LOGIC_ERROR",
    "OSS_READ_FAIL",
    "OSS_WRITE_FAIL",
    "OSS_ETAG_CONFLICT",
    "CLICKHOUSE_CONNECT",
    "WORKSPACE_NOT_FOUND",
    "INPUT_VALIDATION",
)


@dataclass(slots=True)
class FcError(Exception):
    code: str
    message: str
    retriable: bool
    trace_id: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def _new_trace_id() -> str:
    return f"tr-{uuid.uuid4().hex[:12]}"


_OSS_EXC_MODULE = "oss2.exceptions"
_ANTHROPIC_RATE_LIMIT = ("anthropic", "RateLimitError")
_OSS_PRECONDITION_CLASSES = {"PreconditionFailed"}


def classify(exc: BaseException, *, trace_id: str | None = None) -> FcError:
    tid = trace_id or _new_trace_id()
    msg = str(exc) or type(exc).__name__

    # Already-classified errors (e.g. raised by crypto.decrypt_field) pass through;
    # only fill in a trace_id if the caller didn't set one.
    if isinstance(exc, FcError):
        if not exc.trace_id:
            exc.trace_id = tid
        return exc

    if isinstance(exc, ValidationError):
        return FcError("INPUT_VALIDATION", msg, retriable=False, trace_id=tid)

    if isinstance(exc, ConnectionError | socket.gaierror):
        return FcError("CLICKHOUSE_CONNECT", msg, retriable=True, trace_id=tid)

    if isinstance(exc, TimeoutError):
        return FcError("VISTA_COMPUTE_TIMEOUT", msg, retriable=True, trace_id=tid)

    exc_mod = type(exc).__module__
    exc_cls = type(exc).__name__
    if exc_mod.startswith(_OSS_EXC_MODULE):
        if exc_cls in _OSS_PRECONDITION_CLASSES:
            return FcError("OSS_ETAG_CONFLICT", msg, retriable=True, trace_id=tid)
        return FcError("OSS_READ_FAIL", msg, retriable=True, trace_id=tid)

    if (exc_mod.split(".")[0], exc_cls) == _ANTHROPIC_RATE_LIMIT:
        return FcError("VISTA_LLM_RATE_LIMIT", msg, retriable=True, trace_id=tid)

    return FcError("VISTA_LOGIC_ERROR", msg, retriable=False, trace_id=tid)
