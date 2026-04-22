from __future__ import annotations

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_filter import FactorFilterInput, FactorFilterOutput


def test_input_defaults() -> None:
    m = FactorFilterInput(factors_db_uri="oss://b/x.duckdb")
    assert m.problem_codes == []
    assert m.route_codes == []
    assert m.filter_methods == []
    assert m.positive_extractor == "ratio_across_problems"
    assert m.positive_metric == "绝对收益"
    assert m.positive_threshold == 0.618
    assert m.n == 20
    assert m.creator == "factor_evaluate"


def test_output_lists_toml_artifacts() -> None:
    toml = ArtifactRef(
        kind="toml",
        oss_uri="oss://b/user_data/u/realtime/FTS_001/strategy.toml",
        size_bytes=2_500,
    )
    out = FactorFilterOutput(toml_artifacts=[toml], toml_count=1)
    assert out.toml_count == len(out.toml_artifacts)
