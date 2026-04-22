"""Per-function smoke — skipped unless FC_SMOKE_READY=1 is set in env."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("FC_SMOKE_READY") != "1",
    reason="Set FC_SMOKE_READY=1 after deploying to target env",
)


def _tenant():
    return {
        "user_hash": "u_smoke",
        "workspace_id": "EXP_SMOKE",
        "workspace_kind": "research",
        "run_id": f"smoke-{datetime.now(UTC).isoformat()}",
        "requested_at": datetime.now(UTC).isoformat(),
    }


@pytest.mark.parametrize(
    ("fn", "payload"),
    [
        (
            "factor-detect",
            {"factors_db_uri": "oss://vista-fc-dev/_smoke/empty.duckdb"},
        ),
        (
            "factor-duplicate",
            {
                "factors_db_uri": "oss://vista-fc-dev/_smoke/empty.duckdb",
                "route_codes": ["R001"],
                "problem_codes": ["P001"],
            },
        ),
        (
            "factor-evaluate",
            {
                "factors_db_uri": "oss://vista-fc-dev/_smoke/empty.duckdb",
                "route_codes": ["R001"],
                "problem_codes": ["P001"],
                "models": ["MA001"],
            },
        ),
        (
            "factor-filter",
            {"factors_db_uri": "oss://vista-fc-dev/_smoke/empty.duckdb"},
        ),
    ],
)
def test_smoke_function(fc_invoke, fn: str, payload: dict) -> None:
    body = fc_invoke(fn, {"tenant": _tenant(), "payload": payload})
    assert body["status"] in {"succeeded", "failed", "partial"}
    assert body["tenant"]["user_hash"] == "u_smoke"
