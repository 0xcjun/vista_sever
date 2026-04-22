from __future__ import annotations

import pytest
from pydantic import ValidationError

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_evaluate import (
    FactorEvaluateInput,
    FactorEvaluateOutput,
)


def test_input_models_xor_models_config_uri() -> None:
    m1 = FactorEvaluateInput(
        factors_db_uri="oss://b/x.duckdb",
        route_codes=["R1"],
        problem_codes=["P1"],
        models=["MA001", "CSSorting_equal"],
    )
    assert m1.models is not None

    m2 = FactorEvaluateInput(
        factors_db_uri="oss://b/x.duckdb",
        route_codes=["R1"],
        problem_codes=["P1"],
        models_config_uri="oss://b/models.toml",
    )
    assert m2.models_config_uri is not None

    with pytest.raises(ValidationError):
        FactorEvaluateInput(
            factors_db_uri="oss://b/x.duckdb",
            route_codes=["R1"],
            problem_codes=["P1"],
            models=["MA001"],
            models_config_uri="oss://b/models.toml",
        )


def test_output_carries_counts() -> None:
    out = FactorEvaluateOutput(
        total_evaluations=500,
        succeeded=480,
        failed=20,
        report_artifact=ArtifactRef(
            kind="report_json",
            oss_uri="oss://b/eval_report.json",
            size_bytes=8_000,
        ),
    )
    assert out.succeeded + out.failed == out.total_evaluations
