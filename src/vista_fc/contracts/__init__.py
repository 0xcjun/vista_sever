"""Pydantic DTO contracts for all 8 FC handlers."""

from __future__ import annotations

from vista_fc.contracts.common import (
    ArtifactRef,
    EnvelopeIn,
    EnvelopeOut,
    ErrorInfo,
    TenantContext,
)
from vista_fc.contracts.factor_builder import (
    FactorBuilderInput,
    FactorBuilderOutput,
    RouteBuildStat,
)
from vista_fc.contracts.factor_detect import FactorDetectInput, FactorDetectOutput
from vista_fc.contracts.factor_duplicate import (
    FactorDuplicateInput,
    FactorDuplicateOutput,
)
from vista_fc.contracts.factor_evaluate import (
    FactorEvaluateInput,
    FactorEvaluateOutput,
)
from vista_fc.contracts.factor_filter import FactorFilterInput, FactorFilterOutput
from vista_fc.contracts.factor_plan import (
    FactorPlanInput,
    FactorPlanOutput,
    FactorRouteSummary,
)
from vista_fc.contracts.strategy_backtest import (
    StrategyBacktestInput,
    StrategyBacktestOutput,
)
from vista_fc.contracts.vista_realtime import (
    SummaryData,
    TimingEntry,
    VistaRealtimeInput,
    VistaRealtimeOutput,
)

__all__ = [
    "ArtifactRef",
    "EnvelopeIn",
    "EnvelopeOut",
    "ErrorInfo",
    "FactorBuilderInput",
    "FactorBuilderOutput",
    "FactorDetectInput",
    "FactorDetectOutput",
    "FactorDuplicateInput",
    "FactorDuplicateOutput",
    "FactorEvaluateInput",
    "FactorEvaluateOutput",
    "FactorFilterInput",
    "FactorFilterOutput",
    "FactorPlanInput",
    "FactorPlanOutput",
    "FactorRouteSummary",
    "RouteBuildStat",
    "StrategyBacktestInput",
    "StrategyBacktestOutput",
    "SummaryData",
    "TenantContext",
    "TimingEntry",
    "VistaRealtimeInput",
    "VistaRealtimeOutput",
]
