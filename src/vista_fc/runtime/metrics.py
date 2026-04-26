"""Structured metric emission — SLS-indexable via the JSON log sink.

Design choice: no separate exporter. Each metric is a JSON log line with a
stable schema ({event: "metric", name, value, unit, ...tags}) that Aliyun SLS
indexes natively once the log topic rule is in place. This avoids an extra
transport on the FC critical path (which would add latency and a failure mode)
and keeps the contract observable locally.

Tags carried on every metric: run_id, user_hash, workspace_id, function_name,
status. The logging redaction filter still applies, so secret-named tags are
sanitized.
"""

from __future__ import annotations

from typing import Literal

from loguru import logger

MetricValue = int | float

_METRIC_EVENT = "metric"

# Canonical metric names — keep stable once released so SLS dashboards keep working.
HANDLER_DURATION_MS = "handler.duration_ms"
HANDLER_STATUS_TOTAL = "handler.status_total"
HANDLER_ERROR_TOTAL = "handler.error_total"


def emit_metric(
    *,
    name: str,
    value: MetricValue,
    unit: str = "",
    status: Literal["succeeded", "failed", "partial"] | None = None,
    error_code: str | None = None,
) -> None:
    """Emit one metric as a structured log record.

    The sink formats each record as a JSON line; a single SLS topic rule maps
    `event=metric` records into the SLS metric store.
    """
    bindings: dict[str, str | int | float] = {"event": _METRIC_EVENT, "metric_name": name, "metric_value": value}
    if unit:
        bindings["metric_unit"] = unit
    if status is not None:
        bindings["metric_status"] = status
    if error_code is not None:
        bindings["metric_error_code"] = error_code
    logger.bind(**bindings).info(f"metric:{name}={value}{unit}")
