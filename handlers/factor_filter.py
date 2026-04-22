"""FC handler for factor-filter."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.factor_filter import FactorFilterInput, FactorFilterOutput
from vista_fc.services.factor_filter import factor_filter_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=FactorFilterInput,
        output_cls=FactorFilterOutput,
        service=factor_filter_service,
        function_name="factor-filter",
    )
