"""FC handler for factor-plan."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.factor_plan import FactorPlanInput, FactorPlanOutput
from vista_fc.services.factor_plan import factor_plan_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=FactorPlanInput,
        output_cls=FactorPlanOutput,
        service=factor_plan_service,
        function_name="factor-plan",
    )
