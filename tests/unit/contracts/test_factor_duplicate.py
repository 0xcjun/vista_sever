from __future__ import annotations

import pytest
from pydantic import ValidationError

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_duplicate import (
    FactorDuplicateInput,
    FactorDuplicateOutput,
)


def test_input_requires_routes_and_problems() -> None:
    with pytest.raises(ValidationError):
        FactorDuplicateInput(
            factors_db_uri="oss://b/x.duckdb",
            route_codes=[],
            problem_codes=["P1"],
        )
    with pytest.raises(ValidationError):
        FactorDuplicateInput(
            factors_db_uri="oss://b/x.duckdb",
            route_codes=["R1"],
            problem_codes=[],
        )


def test_input_threshold_bounds() -> None:
    with pytest.raises(ValidationError):
        FactorDuplicateInput(
            factors_db_uri="oss://b/x.duckdb",
            route_codes=["R1"],
            problem_codes=["P1"],
            threshold=1.5,
        )


def test_output_counts() -> None:
    out = FactorDuplicateOutput(
        total_input=200,
        total_rejected=50,
        total_survived=150,
        elapsed_seconds=1.0,
        report_artifact=ArtifactRef(
            kind="report_json",
            oss_uri="oss://b/duplicate_report.json",
            size_bytes=3_000,
        ),
    )
    assert out.total_rejected + out.total_survived == out.total_input
