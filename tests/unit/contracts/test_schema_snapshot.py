"""Schema snapshots for all 16 DTOs.

When a DTO changes, the snapshot diff shows up in review. Unintended breaks
will fail the test; intended breaks get re-approved with `pytest --snapshot-update`.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from syrupy.assertion import SnapshotAssertion

from vista_fc.contracts import (
    EnvelopeIn,
    EnvelopeOut,
    FactorBuilderInput,
    FactorBuilderOutput,
    FactorDetectInput,
    FactorDetectOutput,
    FactorDuplicateInput,
    FactorDuplicateOutput,
    FactorEvaluateInput,
    FactorEvaluateOutput,
    FactorFilterInput,
    FactorFilterOutput,
    FactorPlanInput,
    FactorPlanOutput,
    StrategyBacktestInput,
    StrategyBacktestOutput,
    VistaRealtimeInput,
    VistaRealtimeOutput,
)

DTO_CLASSES: list[type[BaseModel]] = [
    FactorPlanInput,
    FactorPlanOutput,
    FactorBuilderInput,
    FactorBuilderOutput,
    FactorDetectInput,
    FactorDetectOutput,
    FactorDuplicateInput,
    FactorDuplicateOutput,
    FactorEvaluateInput,
    FactorEvaluateOutput,
    FactorFilterInput,
    FactorFilterOutput,
    StrategyBacktestInput,
    StrategyBacktestOutput,
    VistaRealtimeInput,
    VistaRealtimeOutput,
]


@pytest.mark.parametrize("dto_cls", DTO_CLASSES, ids=lambda c: c.__name__)
def test_dto_schema_snapshot(
    dto_cls: type[BaseModel],
    snapshot: SnapshotAssertion,
) -> None:
    assert dto_cls.model_json_schema() == snapshot(name=dto_cls.__name__)


def test_envelope_generics_are_importable() -> None:
    envin = EnvelopeIn[FactorPlanInput]
    envout = EnvelopeOut[FactorPlanOutput]
    assert envin is not None and envout is not None
