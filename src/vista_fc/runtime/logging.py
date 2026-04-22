"""Structured logging with per-invocation context binding.

`configure_logging` installs a JSON sink on loguru (env `LOG_FORMAT=json`);
`log_context(...)` is a context manager that binds run_id / user_hash /
workspace_id / function_name so every log line within the block carries them.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from collections.abc import Callable, Iterator
from typing import IO, TYPE_CHECKING, Any, TextIO, cast

from loguru import logger

if TYPE_CHECKING:
    from loguru import Message as LoguruMessage


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
            "message": record["message"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
        }
        extra: dict[str, Any] = record["extra"]
        for key in ("run_id", "user_hash", "workspace_id", "function_name", "phase", "request_id"):
            if key in extra:
                payload[key] = extra[key]
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
