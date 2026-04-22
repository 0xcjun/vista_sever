"""FC handler for factor-detect."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.factor_detect import FactorDetectInput, FactorDetectOutput
from vista_fc.services.factor_detect import factor_detect_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=FactorDetectInput,
        output_cls=FactorDetectOutput,
        service=factor_detect_service,
        function_name="factor-detect",
    )
