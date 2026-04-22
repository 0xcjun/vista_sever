from __future__ import annotations

import pytest
from pydantic import ValidationError

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_plan import (
    FactorPlanInput,
    FactorPlanOutput,
    FactorRouteSummary,
)


def test_input_requires_user_input() -> None:
    m = FactorPlanInput(user_input="动量反转")
    assert m.user_input == "动量反转"
    assert m.interactive is False
    assert m.model is None


def test_input_rejects_empty_user_input() -> None:
    with pytest.raises(ValidationError):
        FactorPlanInput(user_input="")


def test_output_carries_routes_and_toml_artifact() -> None:
    out = FactorPlanOutput(
        routes=[
            FactorRouteSummary(code="R001", name="动量组", compute_engine="czsc"),
        ],
        routes_toml_artifact=ArtifactRef(
            kind="toml",
            oss_uri="oss://b/user_data/u/research/EXP_001/factor_routes.toml",
            size_bytes=1024,
        ),
    )
    assert len(out.routes) == 1
    assert out.routes_toml_artifact.kind == "toml"
