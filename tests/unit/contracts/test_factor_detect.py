from __future__ import annotations

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_detect import FactorDetectInput, FactorDetectOutput


def test_input_defaults() -> None:
    m = FactorDetectInput(
        factors_db_uri="oss://b/user_data/u/research/EXP_001/factors.duckdb",
    )
    assert m.max_workers == 4
    assert m.timeout == 60
    assert m.problems_map_uri is None


def test_output_summary() -> None:
    out = FactorDetectOutput(
        total_factors=100,
        passed=95,
        failed=5,
        report_artifact=ArtifactRef(
            kind="report_json",
            oss_uri="oss://b/.../detect_report.json",
            size_bytes=5_000,
        ),
    )
    assert out.passed + out.failed == out.total_factors
