"""FC handler for factor-evaluate."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.factor_evaluate import (
    FactorEvaluateInput,
    FactorEvaluateOutput,
)
from vista_fc.services.factor_evaluate import factor_evaluate_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=FactorEvaluateInput,
        output_cls=FactorEvaluateOutput,
        service=factor_evaluate_service,
        function_name="factor-evaluate",
    )
