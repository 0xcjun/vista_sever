"""Bounded retry with exponential backoff + jitter, for transient network ops.

Intentionally stdlib-only (no tenacity) — the only dep we'd get is retry and a
friendly decorator, neither of which justifies a transitive surface.

Usage::

    @with_retry(
        max_attempts=3,
        base_delay=0.2,
        retriable=_is_transient,
    )
    def head(...) -> ObjectMeta: ...

`retriable` receives the raised exception and must return True iff we should
retry. This is deliberately explicit: silently retrying a PreconditionFailed
would mask optimistic-lock conflicts and turn them into Lost-Updates.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def with_retry(
    *,
    max_attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    retriable: Callable[[BaseException], bool],
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def _decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except BaseException as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt == max_attempts or not retriable(exc):
                        raise
                    # Exponential backoff with full jitter.
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    sleep(random.uniform(0, delay))
            # Unreachable: loop either returns or raises.
            raise RuntimeError("with_retry fell through") from last_exc

        return _wrapper

    return _decorator


def is_transient_oss_error(exc: BaseException) -> bool:
    """Retriable predicate for OSS ops.

    Explicitly NOT retriable:
      - PreconditionFailed (If-Match/If-None-Match signals a real conflict).
      - NoSuchKey / AccessDenied (client errors).
    Transient:
      - ServerError / RequestError (5xx / network) and OSError subclasses.
    """
    mod = type(exc).__module__
    name = type(exc).__name__

    # Never retry OSS 4xx: precondition / not found / auth. Everything else
    # (ServerError / RequestError / Timeout) is transient.
    if mod.startswith("oss2.exceptions"):
        return name not in {"PreconditionFailed", "NoSuchKey", "NoSuchBucket", "AccessDenied", "InvalidArgument"}

    # boto3/S3-compat: never retry 412 precondition (PutObject with If-Match/If-None-Match).
    if mod.startswith("botocore.exceptions"):
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else ""
        return code not in {"PreconditionFailed", "NoSuchKey", "AccessDenied", "InvalidAccessKeyId"}

    # Low-level network: always transient.
    return isinstance(exc, ConnectionError | TimeoutError | OSError)
