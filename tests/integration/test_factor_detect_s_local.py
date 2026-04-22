"""End-to-end via `s local invoke` (skipped without docker + s CLI + image)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.s_local


def test_factor_detect_end_to_end(s_local_runner, seeded_oss) -> None:
    uri = seeded_oss.put_fixture(
        "mini_factors.duckdb",
        target="user_data/u_itest/research/EXP_IT_0001/factors.duckdb",
    )

    event = {
        "tenant": {
            "user_hash": "u_itest",
            "workspace_id": "EXP_IT_0001",
            "workspace_kind": "research",
            "run_id": "run-itest-0001",
            "requested_at": datetime.now(UTC).isoformat(),
        },
        "payload": {
            "factors_db_uri": uri,
            "max_workers": 2,
            "timeout": 30,
        },
    }

    res = s_local_runner("factor-detect", event, timeout=180)
    assert res.status_code == 0, f"s local invoke non-zero:\n{res.stderr}"
    body = res.json()
    assert body["status"] in {"succeeded", "failed", "partial"}
    assert body["tenant"]["run_id"] == "run-itest-0001"
